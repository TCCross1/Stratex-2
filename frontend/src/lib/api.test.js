import { openContractorPdf, normalizeBlobError } from "./api";
import { nxOpenManifestJson, nxOpenReportHtml } from "../nextgen/api";
import { api as libApi } from "./api";

// We will mock the global objects to verify their calls and behavior
describe("Stratex core - PR #1 Hardening and Verification", () => {
  let mockWindowOpen;
  let mockCreateObjectURL;
  let mockRevokeObjectURL;
  let mockAnchor;
  let mockFileReader;
  let originalFileReader;

  beforeEach(() => {
    // Mock window.open
    mockWindowOpen = jest.fn();
    global.window.open = mockWindowOpen;
    global.alert = jest.fn();

    // Mock URL functions
    mockCreateObjectURL = jest.fn(() => "blob:mock-url");
    mockRevokeObjectURL = jest.fn();
    global.URL.createObjectURL = mockCreateObjectURL;
    global.URL.revokeObjectURL = mockRevokeObjectURL;

    // Mock document.createElement for anchor behavior
    mockAnchor = {
      click: jest.fn(),
      style: {},
      href: "",
      download: "",
    };
    jest.spyOn(document, "createElement").mockImplementation((tagName) => {
      if (tagName === "a") {
        return mockAnchor;
      }
      return {};
    });
    jest.spyOn(document.body, "appendChild").mockImplementation(() => {});
    jest.spyOn(document.body, "removeChild").mockImplementation(() => {});

    // Save original FileReader
    originalFileReader = global.FileReader;
    // Mock FileReader
    class MockFileReader {
      readAsText(blob) {
        this.result = blob._mockText || "";
        if (this.onload) {
          this.onload();
        }
      }
    }
    global.FileReader = MockFileReader;

    // Clear all mock history
    jest.clearAllMocks();
    jest.useFakeTimers();

    jest.spyOn(libApi, "get").mockImplementation(() => Promise.resolve({ data: new Blob() }));
  });

  afterEach(() => {
    jest.useRealTimers();
    global.FileReader = originalFileReader;
    jest.restoreAllMocks();
  });

  // 1. Successful authenticated PDF request & 5. Successful blob URL creation and delayed revocation
  test("1 & 5. Successful authenticated PDF request, blob URL creation, and delayed revocation", async () => {
    const mockWindowInstance = {
      opener: {},
      document: {
        write: jest.fn(),
        close: jest.fn(),
      },
      location: { href: "" },
    };
    mockWindowOpen.mockReturnValue(mockWindowInstance);

    // Mock successful api response
    jest.spyOn(libApi, "get").mockResolvedValue({
      data: new Blob(["pdf-content"], { type: "application/pdf" }),
    });

    const resultPromise = openContractorPdf("job-123");

    // 2. Preview window opened before the asynchronous request completes
    expect(mockWindowOpen).toHaveBeenCalledTimes(1);
    expect(mockWindowOpen).toHaveBeenCalledWith("", "_blank", "noopener,noreferrer");
    expect(mockWindowInstance.opener).toBeNull();
    expect(mockWindowInstance.document.write).toHaveBeenCalledWith(expect.stringContaining("Loading PDF..."));

    const w = await resultPromise;
    expect(w).toBe(mockWindowInstance);
    expect(mockCreateObjectURL).toHaveBeenCalledTimes(1);
    expect(mockWindowInstance.location.href).toBe("blob:mock-url");

    // Check delayed revocation (120000ms / 2 minutes)
    expect(mockRevokeObjectURL).not.toHaveBeenCalled();
    jest.advanceTimersByTime(120000);
    expect(mockRevokeObjectURL).toHaveBeenCalledWith("blob:mock-url");
  });

  // 3. Popup blocked because window.open returns null
  test("3. Popup blocked because window.open returns null throws descriptive error", async () => {
    mockWindowOpen.mockReturnValue(null);

    await expect(openContractorPdf("job-123")).rejects.toThrow(
      "Popup blocked. Please allow popups for this site to view the PDF report."
    );
    expect(libApi.get).not.toHaveBeenCalled();
  });

  // 4. Network/API failure closes the temporary window
  test("4. Network/API failure closes the temporary window", async () => {
    const mockWindowInstance = {
      opener: {},
      document: {
        write: jest.fn(),
        close: jest.fn(),
      },
      location: { href: "" },
      close: jest.fn(),
    };
    mockWindowOpen.mockReturnValue(mockWindowInstance);

    const apiError = new Error("Network Error");
    jest.spyOn(libApi, "get").mockRejectedValue(apiError);

    await expect(openContractorPdf("job-123")).rejects.toThrow("Network Error");
    expect(mockWindowInstance.close).toHaveBeenCalledTimes(1);
  });

  // 6. Blob JSON error response produces the backend detail message
  test("6. Blob JSON error response produces the backend detail message", async () => {
    const errorJson = { detail: "Backend validation failed" };
    const errorBlob = new Blob([JSON.stringify(errorJson)], { type: "application/json" });
    errorBlob._mockText = JSON.stringify(errorJson);

    const errObj = {
      response: {
        data: errorBlob,
      },
    };

    const result = await normalizeBlobError(errObj);
    expect(result).toBe("Backend validation failed");
  });

  // 7. Malformed Blob error returns the fallback message
  test("7. Malformed Blob error returns the fallback message", async () => {
    const malformedBlob = new Blob(["invalid-json{"], { type: "application/json" });
    malformedBlob._mockText = "invalid-json{";

    const errObj = {
      response: {
        data: malformedBlob,
      },
    };

    const result = await normalizeBlobError(errObj);
    expect(result).toBe("An unexpected error occurred");
  });

  // 8. Manifest download creates and clicks a temporary anchor
  // 9. Manifest filename is meaningful and ends in .json
  // 10. Temporary anchor is removed
  test("8, 9, 10. Manifest download creates and clicks a temporary anchor with meaningful name and cleans up", async () => {
    const mockManifestData = { version: "1.0.0" };
    jest.spyOn(libApi, "get").mockResolvedValue({
      data: new Blob([JSON.stringify(mockManifestData)], { type: "application/json" }),
    });

    await nxOpenManifestJson("pkg-456");

    expect(document.createElement).toHaveBeenCalledWith("a");
    expect(mockAnchor.download).toBe("manifest-pkg-456.json"); // Ends in .json, is meaningful
    expect(mockAnchor.href).toBe("blob:mock-url");
    expect(mockAnchor.click).toHaveBeenCalledTimes(1);
    expect(document.body.appendChild).toHaveBeenCalledWith(mockAnchor);
    expect(document.body.removeChild).toHaveBeenCalledWith(mockAnchor);

    // Verify delayed revocation
    expect(mockRevokeObjectURL).not.toHaveBeenCalled();
    jest.advanceTimersByTime(120000);
    expect(mockRevokeObjectURL).toHaveBeenCalledWith("blob:mock-url");
  });

  // 13. No alert() usage remains in the modified workflow
  test("13. No alert() usage is imported/called by our functions", async () => {
    const mockWindowInstance = {
      opener: {},
      document: {
        write: jest.fn(),
        close: jest.fn(),
      },
      location: { href: "" },
    };
    mockWindowOpen.mockReturnValue(mockWindowInstance);
    jest.spyOn(libApi, "get").mockResolvedValue({
      data: new Blob(["pdf-content"], { type: "application/pdf" }),
    });

    await openContractorPdf("job-123");
    expect(global.alert).not.toHaveBeenCalled();
  });

  // 14. Removed insecure URL helpers have no remaining references
  test("14. Removed insecure URL helpers are not present in api exports", () => {
    const apiModule = require("./api");
    const nextgenApiModule = require("../nextgen/api");

    expect(apiModule.contractorPdfUrl).toBeUndefined();
    expect(nextgenApiModule.nxManifestJsonUrl).toBeUndefined();
    expect(nextgenApiModule.nxHabitatReportHtmlUrl).toBeUndefined();
  });
});
