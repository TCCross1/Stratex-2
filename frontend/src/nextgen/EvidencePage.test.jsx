import React from "react";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import EvidencePage from "./EvidencePage";
import { nxOpenManifestJson } from "./api";

// Mock the API helpers from nextgen/api
jest.mock("./api", () => ({
  nxGetMission: jest.fn().mockResolvedValue({
    mission: { product: "product-123", canonical_id: "mission-123", stage: 5 },
    property: { address: { line1: "123 Main St", city: "Seattle", region: "WA" } },
    product: { display_name: "Product 123" },
    stage_labels: ["Stage 1", "Stage 2", "Stage 3", "Stage 4", "Stage 5", "Stage 6"],
  }),
  nxEvidenceProfile: jest.fn().mockResolvedValue({
    display_name: "Profile 123",
    product_key: "prod-key",
    requirements: [
      { category: "RGB_IMAGE", label: "RGB Image", min_count: 1, required: true },
    ],
  }),
  nxListEvidence: jest.fn().mockResolvedValue({ items: [] }),
  nxUploadEvidence: jest.fn(),
  nxValidatePackage: jest.fn().mockResolvedValue({ overall: "PASS", results: [] }),
  nxFinalizePackage: jest.fn(),
  nxListPackages: jest.fn().mockResolvedValue({
    items: [
      { status: "finalized", canonical_id: "pkg-123", package_version: "1", manifest_digest: "digest-123" },
    ],
  }),
  nxOpenManifestJson: jest.fn(),
  nxGetEvidence: jest.fn(),
  nxDeleteEvidence: jest.fn(),
  nxRetryMetadata: jest.fn(),
}));

describe("EvidencePage component - Manifest download controls", () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  const renderComponent = (missionId = "mission-123") => {
    return render(
      <MemoryRouter initialEntries={[`/nextgen/missions/${missionId}/evidence`]}>
        <Routes>
          <Route path="/nextgen/missions/:missionId/evidence" element={<EvidencePage />} />
        </Routes>
      </MemoryRouter>
    );
  };

  test("renders EvidencePage with finalized package and download manifest button", async () => {
    renderComponent();

    // Verify component renders
    expect(await screen.findByTestId("nx-evidence")).toBeInTheDocument();

    // Verify manifest download button is present
    const manifestBtn = await screen.findByTestId("nx-download-manifest");
    expect(manifestBtn).toBeInTheDocument();
    expect(manifestBtn).not.toBeDisabled();
    expect(screen.queryByText("Downloading manifest...")).not.toBeInTheDocument();
  });

  test("clicking manifest download button triggers nxOpenManifestJson and manages loading state", async () => {
    let resolveManifest;
    const manifestPromise = new Promise((resolve) => {
      resolveManifest = resolve;
    });
    nxOpenManifestJson.mockImplementation(() => manifestPromise);

    renderComponent();

    const manifestBtn = await screen.findByTestId("nx-download-manifest");
    fireEvent.click(manifestBtn);

    // 1. Triggered with correct package ID
    expect(nxOpenManifestJson).toHaveBeenCalledWith("pkg-123");

    // 2. Loading state active
    expect(manifestBtn).toBeDisabled();
    expect(screen.getByText("Downloading manifest...")).toBeInTheDocument();

    // 3. Resolve API
    resolveManifest();
    await waitFor(() => {
      expect(manifestBtn).not.toBeDisabled();
    });
    expect(screen.queryByText("Downloading manifest...")).not.toBeInTheDocument();
  });

  test("prevents duplicate manifest requests while busy", async () => {
    let resolveManifest;
    const manifestPromise = new Promise((resolve) => {
      resolveManifest = resolve;
    });
    nxOpenManifestJson.mockImplementation(() => manifestPromise);

    renderComponent();

    const manifestBtn = await screen.findByTestId("nx-download-manifest");
    
    // First click
    fireEvent.click(manifestBtn);
    expect(nxOpenManifestJson).toHaveBeenCalledTimes(1);

    // Second click
    fireEvent.click(manifestBtn);
    expect(nxOpenManifestJson).toHaveBeenCalledTimes(1);

    resolveManifest();
    await waitFor(() => {
      expect(manifestBtn).not.toBeDisabled();
    });
  });

  test("failed manifest download displays error panel and resets loading state", async () => {
    const errorMsg = "Failed to fetch manifest from remote store";
    nxOpenManifestJson.mockRejectedValue(new Error(errorMsg));

    renderComponent();

    const manifestBtn = await screen.findByTestId("nx-download-manifest");
    fireEvent.click(manifestBtn);

    // Error is set in page and rendered
    const errorPanel = await screen.findByText(errorMsg);
    expect(errorPanel).toBeInTheDocument();

    // Loading state is cleared on failure
    expect(manifestBtn).not.toBeDisabled();
    expect(screen.queryByText("Downloading manifest...")).not.toBeInTheDocument();
  });
});
