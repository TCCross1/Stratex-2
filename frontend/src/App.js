import "@/App.css";
import { BrowserRouter, Routes, Route } from "react-router-dom";
import Nav from "@/components/Nav";
import Landing from "@/pages/Landing";
import NewMission from "@/pages/NewMission";
import MissionDashboard from "@/pages/MissionDashboard";
import Projects from "@/pages/Projects";
import Fleet from "@/pages/Fleet";
import Reports from "@/pages/Reports";
import { Toaster } from "sonner";

function App() {
  return (
    <div className="App min-h-screen bg-obsidian text-silver">
      <BrowserRouter>
        <Nav />
        <Routes>
          <Route path="/" element={<Landing />} />
          <Route path="/mission/new" element={<NewMission />} />
          <Route path="/mission/:id" element={<MissionDashboard />} />
          <Route path="/projects" element={<Projects />} />
          <Route path="/fleet" element={<Fleet />} />
          <Route path="/reports" element={<Reports />} />
        </Routes>
        <Toaster
          theme="dark"
          position="top-right"
          toastOptions={{
            style: {
              background: "#10141D",
              border: "1px solid rgba(0,240,255,0.35)",
              color: "#E2E8F0",
              fontFamily: "JetBrains Mono, monospace",
              fontSize: "12px",
              letterSpacing: "0.08em",
              textTransform: "uppercase",
            },
          }}
        />
      </BrowserRouter>
    </div>
  );
}

export default App;
