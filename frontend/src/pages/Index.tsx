import { motion } from "framer-motion";
import { Link } from "react-router-dom";
import { Droplets, Cpu, Activity, MapPin, ArrowRight, Upload, BarChart3, Shield } from "lucide-react";
import { Button } from "@/components/ui/button";
import Navbar from "@/components/Navbar";
import team1 from "@/assets/team-6.jpg";
import team2 from "@/assets/team-1.jpg";
import team3 from "@/assets/team-2.jpg";
import team4 from "@/assets/team-3.jpg";
import team5 from "@/assets/team-5.jpg";
import team6 from "@/assets/team-4.jpg";

const fadeUp = {
  initial: { opacity: 0, y: 30 },
  animate: { opacity: 1, y: 0 },
  transition: { duration: 0.6 },
};

const steps = [
  { icon: Upload, title: "Upload Sample", desc: "Drag & drop your water sample image for analysis" },
  { icon: Cpu, title: "AI Analysis", desc: "YOLOv8 detects and classifies microplastic particles" },
  { icon: BarChart3, title: "Get Insights", desc: "View contamination levels, types, and health risks" },
];

const features = [
  { icon: Cpu, title: "AI Detection", desc: "YOLOv8-powered real-time microplastic identification with 95%+ accuracy" },
  { icon: Activity, title: "IoT Integration", desc: "Live sensor data from water monitoring stations worldwide" },
  { icon: MapPin, title: "Geospatial Mapping", desc: "Interactive contamination heatmaps with hotspot detection" },
  { icon: Shield, title: "Health Risk Assessment", desc: "Life expectancy reduction metrics based on exposure data" },
];

const Index = () => (
  <div className="min-h-screen bg-background">
    <Navbar />

    {/* Hero */}
    <section className="relative min-h-screen flex items-center justify-center overflow-hidden pt-16">
      <div className="absolute inset-0 grid-pattern opacity-30" />
      <div className="absolute top-1/4 left-1/2 -translate-x-1/2 w-[600px] h-[600px] rounded-full bg-primary/5 blur-[120px]" />

      <div className="container relative z-10 text-center max-w-4xl">
        <motion.div {...fadeUp}>
          <div className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full border border-primary/30 bg-primary/5 text-primary text-sm font-medium mb-8">
            <Droplets className="w-4 h-4" />
            Environmental Intelligence Platform
          </div>
        </motion.div>

        <motion.h1
          {...fadeUp}
          transition={{ delay: 0.1, duration: 0.6 }}
          className="text-4xl sm:text-5xl md:text-7xl font-black tracking-tight leading-[1.1] mb-6"
        >
          AI-Powered Detection of{" "}
          <span className="text-gradient">Microplastics</span>{" "}
          in Water
        </motion.h1>

        <motion.p
          {...fadeUp}
          transition={{ delay: 0.2, duration: 0.6 }}
          className="text-lg md:text-xl text-muted-foreground max-w-2xl mx-auto mb-10"
        >
          Combining computer vision, IoT sensors, and health analytics to protect
          water quality and human health across the globe.
        </motion.p>

        <motion.div {...fadeUp} transition={{ delay: 0.3, duration: 0.6 }} className="flex flex-col sm:flex-row gap-4 justify-center">
          <Link to="/upload">
            <Button size="lg" className="bg-primary text-primary-foreground hover:bg-primary/90 gap-2 px-8 h-12 text-base">
              Analyze Your Water Sample
              <ArrowRight className="w-4 h-4" />
            </Button>
          </Link>
          <Link to="/dashboard">
            <Button size="lg" variant="outline" className="h-12 text-base border-border hover:bg-secondary">
              View Dashboard
            </Button>
          </Link>
        </motion.div>
      </div>
    </section>

    {/* Problem */}
    <section className="py-24 bg-surface-1">
      <div className="container max-w-4xl text-center">
        <motion.div initial={{ opacity: 0 }} whileInView={{ opacity: 1 }} viewport={{ once: true }}>
          <h2 className="text-3xl md:text-4xl font-bold mb-6">The Invisible Threat</h2>
          <p className="text-muted-foreground text-lg leading-relaxed">
            Over <span className="text-foreground font-semibold">14 million tons</span> of microplastics
            contaminate our oceans annually. These particles — smaller than 5mm — enter our drinking water,
            food chain, and bodies. Studies link microplastic exposure to inflammation, hormonal disruption,
            and reduced life expectancy. Project ELLE makes this invisible crisis visible and actionable.
          </p>
        </motion.div>
      </div>
    </section>

    {/* How it works */}
    <section className="py-24">
      <div className="container">
        <motion.div initial={{ opacity: 0 }} whileInView={{ opacity: 1 }} viewport={{ once: true }} className="text-center mb-16">
          <h2 className="text-3xl md:text-4xl font-bold mb-4">How It Works</h2>
          <p className="text-muted-foreground">Three steps to actionable water quality insights</p>
        </motion.div>

        <div className="grid md:grid-cols-3 gap-8 max-w-4xl mx-auto">
          {steps.map((step, i) => (
            <motion.div
              key={step.title}
              initial={{ opacity: 0, y: 30 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ delay: i * 0.15 }}
              className="glass rounded-2xl p-8 text-center group hover:glow-border transition-shadow"
            >
              <div className="w-14 h-14 rounded-xl bg-primary/10 flex items-center justify-center mx-auto mb-5 group-hover:bg-primary/20 transition-colors">
                <step.icon className="w-7 h-7 text-primary" />
              </div>
              <div className="text-xs text-primary font-mono mb-2">STEP {i + 1}</div>
              <h3 className="text-lg font-semibold mb-2">{step.title}</h3>
              <p className="text-sm text-muted-foreground">{step.desc}</p>
            </motion.div>
          ))}
        </div>
      </div>
    </section>

    {/* Features */}
    <section className="py-24 bg-surface-1">
      <div className="container">
        <motion.div initial={{ opacity: 0 }} whileInView={{ opacity: 1 }} viewport={{ once: true }} className="text-center mb-16">
          <h2 className="text-3xl md:text-4xl font-bold mb-4">Platform Features</h2>
          <p className="text-muted-foreground">Built for researchers, labs, and environmental agencies</p>
        </motion.div>

        <div className="grid md:grid-cols-2 gap-6 max-w-4xl mx-auto">
          {features.map((f, i) => (
            <motion.div
              key={f.title}
              initial={{ opacity: 0, x: i % 2 === 0 ? -20 : 20 }}
              whileInView={{ opacity: 1, x: 0 }}
              viewport={{ once: true }}
              transition={{ delay: i * 0.1 }}
              className="glass rounded-xl p-6 flex gap-4 items-start hover:glow-border transition-shadow"
            >
              <div className="w-10 h-10 rounded-lg bg-primary/10 flex items-center justify-center shrink-0">
                <f.icon className="w-5 h-5 text-primary" />
              </div>
              <div>
                <h3 className="font-semibold mb-1">{f.title}</h3>
                <p className="text-sm text-muted-foreground">{f.desc}</p>
              </div>
            </motion.div>
          ))}
        </div>
      </div>
    </section>

    {/* Team */}
    <section className="py-24">
      <div className="container">
        <motion.div initial={{ opacity: 0 }} whileInView={{ opacity: 1 }} viewport={{ once: true }} className="text-center mb-16">
          <h2 className="text-3xl md:text-4xl font-bold mb-4">Meet Our Team</h2>
          <p className="text-muted-foreground">The researchers and engineers behind Project ELLE</p>
        </motion.div>

        <div className="grid grid-cols-2 md:grid-cols-3 gap-8 max-w-4xl mx-auto">
          {[
            { img: team1, name: "Nabh Garg", role: "DevOps Engineer" },
            { img: team2, name: "Shruti Dewaskar", role: "Machine Learning Engineer" },
            { img: team3, name: "Riddhiraj Roy", role: "Research Analyst" },
            { img: team4, name: "Shristi Jha", role: "Developer & Documentation Engineer" },
            { img: team5, name: "Vaibhav Mishra", role: "Research Analyst" },
            { img: team6, name: "Ayush Chandra", role: "Machine Learning Engineer" },
          ].map((member, i) => (
            <motion.div
              key={member.name}
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ delay: i * 0.1 }}
              className="text-center group"
            >
              <div className="w-28 h-28 md:w-32 md:h-32 mx-auto mb-4 rounded-full overflow-hidden ring-2 ring-primary/20 group-hover:ring-primary/50 transition-all">
                <img src={member.img} alt={member.name} loading="lazy" width={512} height={512} className="w-full h-full object-cover" />
              </div>
              <h3 className="font-semibold text-sm md:text-base">{member.name}</h3>
              <p className="text-xs md:text-sm text-muted-foreground">{member.role}</p>
            </motion.div>
          ))}
        </div>
      </div>
    </section>

    {/* CTA */}
    <section className="py-24">
      <div className="container text-center max-w-2xl">
        <motion.div initial={{ opacity: 0, y: 20 }} whileInView={{ opacity: 1, y: 0 }} viewport={{ once: true }}>
          <h2 className="text-3xl md:text-4xl font-bold mb-6">Start Protecting Water Quality Today</h2>
          <p className="text-muted-foreground mb-8">
            Upload your first water sample and get detailed microplastic analysis in seconds.
          </p>
          <Link to="/upload">
            <Button size="lg" className="bg-primary text-primary-foreground hover:bg-primary/90 gap-2 px-8 h-12 text-base">
              Analyze Your Water Sample
              <ArrowRight className="w-4 h-4" />
            </Button>
          </Link>
        </motion.div>
      </div>
    </section>

    {/* Footer */}
    <footer className="border-t border-border py-8">
      <div className="container flex flex-col sm:flex-row items-center justify-between gap-4 text-sm text-muted-foreground">
        <div className="flex items-center gap-2">
          <Droplets className="w-4 h-4 text-primary" />
          <span>Project ELLE © 2026</span>
        </div>
        <div className="flex gap-6">
          <Link to="/dashboard" className="hover:text-foreground transition-colors">Dashboard</Link>
          <Link to="/upload" className="hover:text-foreground transition-colors">Analyze</Link>
          <Link to="/map" className="hover:text-foreground transition-colors">Map</Link>
        </div>
      </div>
    </footer>
  </div>
);

export default Index;
