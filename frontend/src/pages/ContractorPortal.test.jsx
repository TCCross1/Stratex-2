import React from "react";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { JobDetail } from "./ContractorPortal";
import {
  openContractorPdf,
  getContractorJob,
  listContractorJobs,
  getMaterials,
  getJobAuditLog,
  rescheduleSuggestions,
  weatherMonitor
} from "@/lib/api";
import { toast } from "sonner";

// Mock router and hook dependencies
jest.mock("../lib/auth", () => ({
  useAuth: () => ({
    user: { email: "contractor@example.com", role: "contractor" },
    token: "mock-token",
  }),
}));

jest.mock("../hooks/use-is-mobile", () => () => false);

jest.mock("sonner", () => ({
  toast: {
    error: jest.fn(),
    success: jest.fn(),
  },
}));

// Mock out all the sub-components to isolate ContractorPortal testing and bypass canvas/Leaflet/3D dependencies
jest.mock("../components/RoofModel3D", () => () => <div data-testid="mock-roof-model" />);
jest.mock("../components/ForensicOverlay", () => {
  return {
    __esModule: true,
    default: () => <div data-testid="mock-forensic-overlay" />,
    AnomalySelector: () => <div data-testid="mock-anomaly-selector" />,
    ProjectIdentityCard: () => <div data-testid="mock-project-identity-card" />,
    QuantEstimationCard: () => <div data-testid="mock-quant-estimation-card" />,
    AnomalyMonetizationCard: () => <div data-testid="mock-anomaly-monetization-card" />,
  };
});
jest.mock("../components/MapPicker", () => () => <div data-testid="mock-map-picker" />);
jest.mock("../components/LaunchCountdownBadge", () => () => <div data-testid="mock-countdown-badge" />);
jest.mock("../components/CaliperUpload", () => () => <div data-testid="mock-caliper-upload" />);
jest.mock("../components/ValidationReport", () => () => <div data-testid="mock-validation-report" />);
jest.mock("../components/MaterialConfigurator", () => () => <div data-testid="mock-material-configurator" />);

// Mock the API helper module
jest.mock("@/lib/api", () => ({
  listContractorJobs: jest.fn(),
  getContractorJob: jest.fn(),
  getMaterials: jest.fn(),
  openContractorPdf: jest.fn(),
  getJobAuditLog: jest.fn(),
  rescheduleSuggestions: jest.fn(),
  weatherMonitor: jest.fn(),
}));

describe("ContractorPortal component - PDF generation controls", () => {
  beforeEach(() => {
    jest.clearAllMocks();

    listContractorJobs.mockResolvedValue({ items: [] });
    getContractorJob.mockResolvedValue({
      id: "job-123",
      status: "PROPOSAL_READY",
      homeowner_email: "homeowner@example.com",
      materials: {},
      pricing: {
        lock_mode: "firm-fixed",
        line_items: [
          { description: "Test Item", qty: 10, unit: "SQ", unit_price: 150, total: 1500, xactimate_tag: "RF-300" }
        ],
        subtotal: 1500,
        overhead_rate: 0.1,
        overhead: 150,
        profit_rate: 0.1,
        profit: 150,
        insurance_supplement_rate: 0,
        final_total: 1800,
      },
    });
    getMaterials.mockResolvedValue({});
    getJobAuditLog.mockResolvedValue({ events: [] });
    rescheduleSuggestions.mockResolvedValue([]);
    weatherMonitor.mockResolvedValue({});
  });

  const renderComponent = (jobId = "job-123") => {
    return render(
      <MemoryRouter initialEntries={[`/contractor/jobs/${jobId}`]}>
        <Routes>
          <Route path="/contractor/jobs/:id" element={<JobDetail />} />
        </Routes>
      </MemoryRouter>
    );
  };

  test("renders ContractorPortal and checks PDF button features", async () => {
    renderComponent();

    // Verify loading state is initially gone and button is visible
    const pdfBtn = await screen.findByTestId("job-pdf-btn");
    expect(pdfBtn).toBeInTheDocument();
    expect(pdfBtn).not.toBeDisabled();
    expect(screen.queryByText("Loading PDF…")).not.toBeInTheDocument();
  });

  test("clicking PDF button triggers openContractorPdf and manages loading state", async () => {
    let resolvePdf;
    const pdfPromise = new Promise((resolve) => {
      resolvePdf = resolve;
    });
    openContractorPdf.mockImplementation(() => pdfPromise);

    renderComponent();

    const pdfBtn = await screen.findByTestId("job-pdf-btn");
    fireEvent.click(pdfBtn);

    // 1. openContractorPdf has been triggered
    expect(openContractorPdf).toHaveBeenCalledWith("job-123");

    // 2. Loading state is active: button is disabled, showing "Loading PDF…"
    expect(pdfBtn).toBeDisabled();
    expect(screen.getByText("Loading PDF…")).toBeInTheDocument();

    // 3. Resolve the API call
    resolvePdf();
    await waitFor(() => {
      expect(pdfBtn).not.toBeDisabled();
    });
    expect(screen.queryByText("Loading PDF…")).not.toBeInTheDocument();
  });

  test("prevents duplicate PDF requests while busy", async () => {
    let resolvePdf;
    const pdfPromise = new Promise((resolve) => {
      resolvePdf = resolve;
    });
    openContractorPdf.mockImplementation(() => pdfPromise);

    renderComponent();

    const pdfBtn = await screen.findByTestId("job-pdf-btn");
    
    // First click
    fireEvent.click(pdfBtn);
    expect(openContractorPdf).toHaveBeenCalledTimes(1);

    // Click again while busy
    fireEvent.click(pdfBtn);
    // Should still only be called once because it was busy
    expect(openContractorPdf).toHaveBeenCalledTimes(1);

    // Finish first request
    resolvePdf();
    await waitFor(() => {
      expect(pdfBtn).not.toBeDisabled();
    });
  });

  test("failed PDF request closes loading state and shows toast error", async () => {
    const errorMsg = "Network timeout or unauthorized access";
    openContractorPdf.mockRejectedValue(new Error(errorMsg));

    renderComponent();

    const pdfBtn = await screen.findByTestId("job-pdf-btn");
    fireEvent.click(pdfBtn);

    await waitFor(() => {
      expect(toast.error).toHaveBeenCalledWith(errorMsg);
    });

    // Check loading state is cleared on failure
    expect(pdfBtn).not.toBeDisabled();
    expect(screen.queryByText("Loading PDF…")).not.toBeInTheDocument();
  });
});
