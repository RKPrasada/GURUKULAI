"""Seed ALP CBT 2 Part B questions: Electrical stream (38Q) + Mechanical stream (37Q)."""
import json, uuid, random
from pathlib import Path

BANK_DIR = Path(__file__).parent.parent / "data" / "question_banks"

ALP_CBT2 = [
  # ===== ELECTRICAL STREAM (38 questions) =====
  # DC Circuits
  {"subject":"Electrical","topic":"DC Circuits","stream":"electrical","difficulty":1,
   "question_text":"A 12 V battery is connected across a 4 Ω resistor. The current through the circuit is:","options":["3 A","4 A","2 A","48 A"],"correct_index":0,"explanation":"I=V/R=12/4=3 A (Ohm's Law)."},
  {"subject":"Electrical","topic":"DC Circuits","stream":"electrical","difficulty":2,
   "question_text":"Three resistors of 6 Ω, 3 Ω and 2 Ω are connected in parallel. The equivalent resistance is:","options":["1 Ω","11 Ω","0.5 Ω","3.67 Ω"],"correct_index":0,"explanation":"1/R=1/6+1/3+1/2=1/6+2/6+3/6=1. R=1 Ω."},
  {"subject":"Electrical","topic":"DC Circuits","stream":"electrical","difficulty":2,
   "question_text":"Power dissipated in a 10 Ω resistor carrying 2 A current is:","options":["40 W","20 W","10 W","4 W"],"correct_index":0,"explanation":"P=I²R=4×10=40 W."},
  {"subject":"Electrical","topic":"DC Circuits","stream":"electrical","difficulty":2,
   "question_text":"Kirchhoff's Voltage Law states that the algebraic sum of all voltages in a closed loop is:","options":["Zero","Equal to EMF","Equal to total resistance","Equal to current"],"correct_index":0,"explanation":"KVL: ΣV=0 around any closed loop (energy conservation)."},
  {"subject":"Electrical","topic":"DC Circuits","stream":"electrical","difficulty":3,
   "question_text":"A 100 W, 250 V bulb and a 60 W, 250 V bulb are connected in series across 250 V. Which bulb glows brighter?","options":["60 W bulb","100 W bulb","Both equally","Neither glows"],"correct_index":0,"explanation":"In series, same current flows. R(60W)=250²/60≈1042Ω > R(100W)=250²/100=625Ω. Higher resistance → more voltage → more power → 60W bulb glows brighter."},
  {"subject":"Electrical","topic":"DC Circuits","stream":"electrical","difficulty":1,
   "question_text":"The unit of electrical resistance is:","options":["Ohm","Ampere","Volt","Watt"],"correct_index":0,"explanation":"Resistance is measured in Ohms (Ω). Named after Georg Simon Ohm."},
  {"subject":"Electrical","topic":"DC Circuits","stream":"electrical","difficulty":2,
   "question_text":"In a series circuit of R₁=5Ω and R₂=10Ω connected to 30V, voltage across R₂ is:","options":["20 V","10 V","15 V","30 V"],"correct_index":0,"explanation":"I=V/(R₁+R₂)=30/15=2A. V₂=I×R₂=2×10=20V."},
  # AC Circuits
  {"subject":"Electrical","topic":"AC Circuits","stream":"electrical","difficulty":1,
   "question_text":"The frequency of AC supply in India is:","options":["50 Hz","60 Hz","40 Hz","100 Hz"],"correct_index":0,"explanation":"India uses 50 Hz AC supply. USA/Canada use 60 Hz."},
  {"subject":"Electrical","topic":"AC Circuits","stream":"electrical","difficulty":2,
   "question_text":"RMS value of a sinusoidal AC voltage with peak value Vm is:","options":["Vm/√2","Vm/2","√2·Vm","2Vm"],"correct_index":0,"explanation":"VRMS=Vm/√2≈0.707Vm for pure sinusoidal waveform."},
  {"subject":"Electrical","topic":"AC Circuits","stream":"electrical","difficulty":2,
   "question_text":"In a purely inductive AC circuit, current lags voltage by:","options":["90°","0°","45°","180°"],"correct_index":0,"explanation":"In a pure inductor, current lags voltage by 90° (π/2 radians)."},
  {"subject":"Electrical","topic":"AC Circuits","stream":"electrical","difficulty":2,
   "question_text":"Power factor of a purely resistive circuit is:","options":["1","0","0.5","0.866"],"correct_index":0,"explanation":"PF=cosφ. For purely resistive load, φ=0°, PF=cos0°=1."},
  {"subject":"Electrical","topic":"AC Circuits","stream":"electrical","difficulty":3,
   "question_text":"A series RLC circuit has R=10Ω, XL=20Ω, XC=10Ω. The impedance Z is:","options":["√200 Ω ≈14.14Ω","30Ω","10Ω","20Ω"],"correct_index":0,"explanation":"Z=√(R²+(XL-XC)²)=√(100+100)=√200≈14.14Ω."},
  {"subject":"Electrical","topic":"AC Circuits","stream":"electrical","difficulty":2,
   "question_text":"The standard domestic single-phase voltage in India is:","options":["230 V","110 V","415 V","440 V"],"correct_index":0,"explanation":"Single-phase domestic supply in India: 230V (±6%), 50Hz."},
  # Transformers
  {"subject":"Electrical","topic":"Transformers","stream":"electrical","difficulty":1,
   "question_text":"A transformer with primary turns 200 and secondary turns 400, primary voltage 230V. Secondary voltage is:","options":["460 V","115 V","920 V","230 V"],"correct_index":0,"explanation":"V₂/V₁=N₂/N₁ → V₂=230×400/200=460V."},
  {"subject":"Electrical","topic":"Transformers","stream":"electrical","difficulty":2,
   "question_text":"Transformer cores are made of laminated silicon steel to reduce:","options":["Eddy current losses","Copper losses","Hysteresis losses","Iron losses only"],"correct_index":0,"explanation":"Lamination increases resistance to eddy currents, reducing eddy current losses (P∝t², where t=lamination thickness)."},
  {"subject":"Electrical","topic":"Transformers","stream":"electrical","difficulty":2,
   "question_text":"A step-up transformer increases:","options":["Voltage","Current","Power","Both voltage and current"],"correct_index":0,"explanation":"Step-up transformer increases voltage while decreasing current (power stays constant, ignoring losses)."},
  {"subject":"Electrical","topic":"Transformers","stream":"electrical","difficulty":3,
   "question_text":"A transformer has 100% efficiency with input 1000W. If primary current is 5A at 200V, secondary voltage is 400V. Secondary current is:","options":["2.5 A","5 A","10 A","1 A"],"correct_index":0,"explanation":"Power out=Power in=1000W. I₂=P/V₂=1000/400=2.5A."},
  {"subject":"Electrical","topic":"Transformers","stream":"electrical","difficulty":1,
   "question_text":"Transformer oil is used for:","options":["Insulation and cooling","Conduction","Reducing noise","Increasing efficiency"],"correct_index":0,"explanation":"Transformer oil (mineral oil) provides insulation and carries away heat from windings and core."},
  # Electrical Machines
  {"subject":"Electrical","topic":"Electrical Machines","stream":"electrical","difficulty":1,
   "question_text":"The speed of a 4-pole induction motor on 50 Hz supply (synchronous speed) is:","options":["1500 rpm","3000 rpm","750 rpm","1000 rpm"],"correct_index":0,"explanation":"Ns=120f/P=120×50/4=1500 rpm."},
  {"subject":"Electrical","topic":"Electrical Machines","stream":"electrical","difficulty":2,
   "question_text":"The slip of a 3-phase induction motor running at 1440 rpm with synchronous speed 1500 rpm is:","options":["4%","2%","6%","10%"],"correct_index":0,"explanation":"Slip s=(Ns-N)/Ns=(1500-1440)/1500=60/1500=0.04=4%."},
  {"subject":"Electrical","topic":"Electrical Machines","stream":"electrical","difficulty":2,
   "question_text":"A DC motor has back EMF because:","options":["Armature rotates in magnetic field generating EMF opposing supply","Commutator reverses current","Field winding creates opposing flux","Load resistance"],"correct_index":0,"explanation":"When armature rotates, it cuts magnetic flux and generates a back EMF (Eb) opposing the applied voltage (V). Eb=V−IaRa."},
  {"subject":"Electrical","topic":"Electrical Machines","stream":"electrical","difficulty":1,
   "question_text":"The rotor of a squirrel cage induction motor is made of:","options":["Copper/aluminium bars short-circuited at ends","Wound coils with slip rings","Permanent magnets","DC windings"],"correct_index":0,"explanation":"Squirrel cage rotor: conducting bars (Al or Cu) embedded in slots, short-circuited by end rings — no external connections."},
  {"subject":"Electrical","topic":"Electrical Machines","stream":"electrical","difficulty":2,
   "question_text":"Which starting method for a 3-phase induction motor gives the lowest starting current?","options":["Star-Delta starter","Direct On-Line (DOL) starter","Auto-transformer starter","Soft starter"],"correct_index":0,"explanation":"Star-Delta reduces starting voltage by 1/√3, current by 1/3 of DOL current — lowest among mechanical starters."},
  # Measuring Instruments
  {"subject":"Electrical","topic":"Measuring Instruments","stream":"electrical","difficulty":1,
   "question_text":"A voltmeter is always connected:","options":["In parallel with the component","In series with the component","Between earth and neutral","Across the source only"],"correct_index":0,"explanation":"Voltmeter measures potential difference — must be in parallel to avoid disturbing circuit."},
  {"subject":"Electrical","topic":"Measuring Instruments","stream":"electrical","difficulty":2,
   "question_text":"Megger is used to measure:","options":["Insulation resistance","Continuity","Voltage","Earth resistance"],"correct_index":0,"explanation":"Megger (Megohmmeter) measures insulation resistance in MΩ — used to test winding insulation of motors/cables."},
  {"subject":"Electrical","topic":"Measuring Instruments","stream":"electrical","difficulty":2,
   "question_text":"A wattmeter measures:","options":["Real (active) power in watts","Reactive power","Apparent power","Power factor"],"correct_index":0,"explanation":"Wattmeter has current coil (series) and pressure coil (parallel) — deflection∝V×I×cosφ = real power (W)."},
  {"subject":"Electrical","topic":"Measuring Instruments","stream":"electrical","difficulty":1,
   "question_text":"The instrument used to measure insulation resistance between two conductors is:","options":["Megger","Multimeter","Tong tester","Ammeter"],"correct_index":0,"explanation":"Megger applies high DC voltage (500V/1000V) to measure insulation resistance in MΩ."},
  # Wiring & Safety
  {"subject":"Electrical","topic":"Wiring & Safety","stream":"electrical","difficulty":1,
   "question_text":"The colour code of the earth wire in Indian standard wiring is:","options":["Green/Yellow","Red","Black","Blue"],"correct_index":0,"explanation":"IS 694: Earth=Green/Yellow, Phase=Red/Yellow/Blue (3-ph), Neutral=Black."},
  {"subject":"Electrical","topic":"Wiring & Safety","stream":"electrical","difficulty":2,
   "question_text":"An ELCB (Earth Leakage Circuit Breaker) trips when leakage current exceeds:","options":["30 mA","5 A","1 A","100 mA"],"correct_index":0,"explanation":"Standard ELCB/RCCB trips at 30 mA leakage current — this level can cause ventricular fibrillation."},
  {"subject":"Electrical","topic":"Wiring & Safety","stream":"electrical","difficulty":2,
   "question_text":"The purpose of earthing in electrical installations is to:","options":["Provide low resistance path for fault current","Improve power factor","Reduce energy consumption","Increase current capacity"],"correct_index":0,"explanation":"Earthing channels fault current safely to ground, operating the protective device and preventing electric shock."},
  {"subject":"Electrical","topic":"Wiring & Safety","stream":"electrical","difficulty":1,
   "question_text":"MCB stands for:","options":["Miniature Circuit Breaker","Main Current Breaker","Motor Control Box","Magnetic Core Breaker"],"correct_index":0,"explanation":"MCB (Miniature Circuit Breaker) automatically breaks the circuit on overload or short circuit."},
  # Storage Batteries
  {"subject":"Electrical","topic":"Storage Batteries","stream":"electrical","difficulty":1,
   "question_text":"EMF of a fully charged lead-acid cell is approximately:","options":["2.1 V","1.5 V","3.7 V","6 V"],"correct_index":0,"explanation":"Fully charged lead-acid cell: 2.1V. A 12V battery has 6 cells (6×2.1=12.6V)."},
  {"subject":"Electrical","topic":"Storage Batteries","stream":"electrical","difficulty":2,
   "question_text":"During discharge of a lead-acid battery, the specific gravity of electrolyte:","options":["Decreases","Increases","Remains constant","First increases then decreases"],"correct_index":0,"explanation":"H₂SO₄ is consumed during discharge → specific gravity decreases (from ~1.28 charged to ~1.15 discharged)."},
  {"subject":"Electrical","topic":"Storage Batteries","stream":"electrical","difficulty":2,
   "question_text":"The electrolyte used in a lead-acid battery is:","options":["Dilute sulphuric acid","Dilute hydrochloric acid","Potassium hydroxide","Distilled water"],"correct_index":0,"explanation":"Lead-acid battery uses dilute H₂SO₄ (sulphuric acid) as electrolyte."},
  # Electronics basics
  {"subject":"Electrical","topic":"Basic Electronics","stream":"electrical","difficulty":1,
   "question_text":"A diode allows current flow:","options":["In only one direction (forward biased)","In both directions","When reverse biased","Only in AC circuits"],"correct_index":0,"explanation":"A PN junction diode conducts in forward bias (P+, N−) and blocks in reverse bias."},
  {"subject":"Electrical","topic":"Basic Electronics","stream":"electrical","difficulty":2,
   "question_text":"A full-wave bridge rectifier converts AC to DC using:","options":["4 diodes","2 diodes","1 diode","6 diodes"],"correct_index":0,"explanation":"Bridge rectifier uses 4 diodes in a bridge arrangement to use both half-cycles of AC."},
  {"subject":"Electrical","topic":"Basic Electronics","stream":"electrical","difficulty":2,
   "question_text":"The device used to regulate output voltage in a power supply is:","options":["Zener diode","Rectifier diode","LED","Transistor"],"correct_index":0,"explanation":"Zener diode maintains constant voltage in reverse breakdown region — used as voltage regulator."},
  {"subject":"Electrical","topic":"Basic Electronics","stream":"electrical","difficulty":1,
   "question_text":"NPN transistor operates when base is:","options":["Forward biased w.r.t. emitter","Reverse biased","At same potential as collector","At ground potential"],"correct_index":0,"explanation":"NPN transistor: B-E junction forward biased, B-C junction reverse biased for active operation."},
  {"subject":"Electrical","topic":"Basic Electronics","stream":"electrical","difficulty":2,
   "question_text":"The ripple frequency of a full-wave rectifier on 50 Hz supply is:","options":["100 Hz","50 Hz","25 Hz","200 Hz"],"correct_index":0,"explanation":"Full-wave rectifier rectifies both half-cycles → ripple frequency = 2×supply frequency = 2×50=100 Hz."},

  # ===== MECHANICAL STREAM (37 questions) =====
  # Engineering Drawing
  {"subject":"Mechanical","topic":"Engineering Drawing","stream":"mechanical","difficulty":1,
   "question_text":"The scale 1:10 means:","options":["Drawing is 1/10th of actual size","Drawing is 10 times actual size","Drawing equals actual size","None of these"],"correct_index":0,"explanation":"Scale 1:10 = reducing scale. 1 unit on drawing = 10 units actual."},
  {"subject":"Mechanical","topic":"Engineering Drawing","stream":"mechanical","difficulty":2,
   "question_text":"In first angle projection (used in India), the front view is placed:","options":["Below the top view","Above the top view","Left of the side view","Right of the front view"],"correct_index":0,"explanation":"First angle (European) projection: top view is below front view, right side view is placed to the left."},
  {"subject":"Mechanical","topic":"Engineering Drawing","stream":"mechanical","difficulty":2,
   "question_text":"A hidden line in engineering drawing is represented by:","options":["Dashed line","Continuous thick line","Chain line","Zigzag line"],"correct_index":0,"explanation":"Hidden (invisible) edges are shown as short dashed lines (IS specification)."},
  {"subject":"Mechanical","topic":"Engineering Drawing","stream":"mechanical","difficulty":1,
   "question_text":"The tolerance is the difference between:","options":["Upper limit and lower limit","Basic size and actual size","Fit and allowance","Shaft size and hole size"],"correct_index":0,"explanation":"Tolerance = Upper Limit − Lower Limit. It represents permissible variation in size."},
  {"subject":"Mechanical","topic":"Engineering Drawing","stream":"mechanical","difficulty":2,
   "question_text":"An isometric drawing uses equal angles of ___ between each axis:","options":["120°","90°","60°","30°"],"correct_index":0,"explanation":"In isometric projection, all three axes are equally inclined at 120° to each other."},
  # Measurements & Gauges
  {"subject":"Mechanical","topic":"Measurements & Gauges","stream":"mechanical","difficulty":1,
   "question_text":"Least count of a vernier caliper with 50 vernier divisions coinciding with 49 main scale divisions (MSD=1mm) is:","options":["0.02 mm","0.1 mm","0.05 mm","0.01 mm"],"correct_index":0,"explanation":"LC=1 MSD − 1VSD=1−49/50=0.02 mm."},
  {"subject":"Mechanical","topic":"Measurements & Gauges","stream":"mechanical","difficulty":2,
   "question_text":"A micrometer screw gauge has 0.5 mm pitch and thimble has 50 divisions. Least count is:","options":["0.01 mm","0.05 mm","0.1 mm","0.001 mm"],"correct_index":0,"explanation":"LC=Pitch/No. of divisions=0.5/50=0.01 mm."},
  {"subject":"Mechanical","topic":"Measurements & Gauges","stream":"mechanical","difficulty":2,
   "question_text":"GO/NO-GO gauges are used to check:","options":["Limits of size of components","Surface finish","Hardness","Concentricity"],"correct_index":0,"explanation":"Plug gauges (GO end enters, NO-GO end should not enter) verify a hole is within its tolerance limits."},
  {"subject":"Mechanical","topic":"Measurements & Gauges","stream":"mechanical","difficulty":1,
   "question_text":"Surface roughness is measured using a:","options":["Profilometer (Surface Roughness Tester)","Vernier caliper","Dial gauge","Feeler gauge"],"correct_index":0,"explanation":"A profilometer measures Ra (average roughness) of a machined surface in µm."},
  # Workshop Technology: Lathe
  {"subject":"Mechanical","topic":"Lathe Operations","stream":"mechanical","difficulty":1,
   "question_text":"The most widely used holding device on a lathe is:","options":["Three-jaw self-centering chuck","Four-jaw independent chuck","Collet","Face plate"],"correct_index":0,"explanation":"Three-jaw chuck grips round stock automatically; fast and convenient for most turning operations."},
  {"subject":"Mechanical","topic":"Lathe Operations","stream":"mechanical","difficulty":2,
   "question_text":"Taper turning using the tailstock offset method is used for:","options":["Long, slight tapers","Short steep tapers","External threads","Facing"],"correct_index":0,"explanation":"Tailstock offset method: suitable for long gentle tapers. Limitation: cannot turn internal tapers."},
  {"subject":"Mechanical","topic":"Lathe Operations","stream":"mechanical","difficulty":2,
   "question_text":"The cutting speed for turning mild steel with HSS tool is approximately:","options":["25–30 m/min","100–120 m/min","5–10 m/min","200 m/min"],"correct_index":0,"explanation":"HSS tool on mild steel: ~25–30 m/min. Carbide tools can achieve 100+ m/min."},
  {"subject":"Mechanical","topic":"Lathe Operations","stream":"mechanical","difficulty":3,
   "question_text":"A 50 mm diameter bar is to be turned at 300 rpm. Cutting speed=","options":["47.1 m/min","15 m/min","300 m/min","94 m/min"],"correct_index":0,"explanation":"V=πDN/1000=π×50×300/1000=47.1 m/min."},
  {"subject":"Mechanical","topic":"Lathe Operations","stream":"mechanical","difficulty":1,
   "question_text":"Threading on a lathe is done by engaging the:","options":["Half-nut on lead screw","Carriage hand wheel","Cross-slide","Apron handwheel"],"correct_index":0,"explanation":"Engaging the half-nut on the lead screw synchronises tool movement with spindle for thread cutting."},
  # Fitting & Fasteners
  {"subject":"Mechanical","topic":"Fitting & Fasteners","stream":"mechanical","difficulty":1,
   "question_text":"A key is used to:","options":["Prevent relative rotation between shaft and hub","Join two shafts end to end","Prevent axial movement only","Reduce friction"],"correct_index":0,"explanation":"Keys (Woodruff, sunk, feather) fit in keyways on shaft and hub to transmit torque."},
  {"subject":"Mechanical","topic":"Fitting & Fasteners","stream":"mechanical","difficulty":2,
   "question_text":"The pitch of a screw thread is:","options":["Distance between adjacent thread crests","Thread depth","Thread angle","Number of threads per inch"],"correct_index":0,"explanation":"Pitch = axial distance from one thread crest to the next. Lead = pitch × number of starts."},
  {"subject":"Mechanical","topic":"Fitting & Fasteners","stream":"mechanical","difficulty":2,
   "question_text":"Loctite (thread locker) is used to:","options":["Prevent loosening of bolts due to vibration","Join metal surfaces permanently","Cut threads","Lubricate bearings"],"correct_index":0,"explanation":"Thread-locking compounds fill gaps in thread flanks, curing by anaerobic polymerisation to prevent self-loosening."},
  {"subject":"Mechanical","topic":"Fitting & Fasteners","stream":"mechanical","difficulty":1,
   "question_text":"A rivet is a permanent fastener. Which operation is done to fix the rivet?","options":["Riveting (upsetting the tail)","Welding","Bolting","Soldering"],"correct_index":0,"explanation":"The rivet tail is deformed (upset) with a rivet set or hammer to create the closing head."},
  # Welding
  {"subject":"Mechanical","topic":"Welding","stream":"mechanical","difficulty":1,
   "question_text":"The temperature of an oxy-acetylene welding flame is approximately:","options":["3200°C","1500°C","800°C","5000°C"],"correct_index":0,"explanation":"Oxy-acetylene neutral flame: ~3100–3200°C — suitable for most metals."},
  {"subject":"Mechanical","topic":"Welding","stream":"mechanical","difficulty":2,
   "question_text":"In MIG (GMAW) welding, the electrode is:","options":["Continuous consumable wire","Tungsten (non-consumable)","Flux coated rod","Carbon electrode"],"correct_index":0,"explanation":"MIG/GMAW uses a continuously fed consumable wire electrode. The arc melts both wire and base metal."},
  {"subject":"Mechanical","topic":"Welding","stream":"mechanical","difficulty":2,
   "question_text":"Post Weld Heat Treatment (PWHT) is done to:","options":["Relieve residual stresses","Increase hardness","Improve surface finish","Reduce weld size"],"correct_index":0,"explanation":"PWHT (stress relieving) heats the welded assembly to reduce residual stresses and prevent cracking."},
  {"subject":"Mechanical","topic":"Welding","stream":"mechanical","difficulty":1,
   "question_text":"In arc welding, the polarity DCEP (DC Electrode Positive) gives:","options":["More heat at electrode (deeper penetration on base metal)","More heat at work","Less spatter","Faster deposition"],"correct_index":0,"explanation":"DCEP: 2/3 heat at electrode, 1/3 at base metal → good deposition but less penetration. DCEN reverses this."},
  # Heat Treatment
  {"subject":"Mechanical","topic":"Heat Treatment","stream":"mechanical","difficulty":1,
   "question_text":"Annealing of steel is done to:","options":["Soften, relieve stresses and improve machinability","Increase hardness","Increase brittleness","Improve corrosion resistance"],"correct_index":0,"explanation":"Annealing: heat to austenitising temp, soak, slow cool in furnace → soft, ductile, stress-free microstructure."},
  {"subject":"Mechanical","topic":"Heat Treatment","stream":"mechanical","difficulty":2,
   "question_text":"Case hardening is used when the requirement is:","options":["Hard surface with tough core","Uniform hardness throughout","Soft surface with hard core","Maximum ductility"],"correct_index":0,"explanation":"Case hardening (carburising, nitriding, induction hardening) gives wear-resistant surface while maintaining tough core — used for gears, crankshafts."},
  {"subject":"Mechanical","topic":"Heat Treatment","stream":"mechanical","difficulty":2,
   "question_text":"Quenching medium that gives the least severe quench:","options":["Oil","Water","Brine","Air"],"correct_index":3,"explanation":"Quench severity: Brine > Water > Oil > Air. Air quench is least severe — used for air-hardening tool steels."},
  # Fluid Mechanics & Hydraulics
  {"subject":"Mechanical","topic":"Fluid Mechanics","stream":"mechanical","difficulty":1,
   "question_text":"Pascal's Law states that pressure applied to an enclosed fluid is transmitted:","options":["Equally in all directions","Only downward","Only in direction of force","Upward only"],"correct_index":0,"explanation":"Pascal's law: pressure in an enclosed fluid is transmitted undiminished in all directions."},
  {"subject":"Mechanical","topic":"Fluid Mechanics","stream":"mechanical","difficulty":2,
   "question_text":"A hydraulic jack uses the principle of:","options":["Pascal's Law with area ratio for force multiplication","Archimedes Principle","Bernoulli's Theorem","Boyle's Law"],"correct_index":0,"explanation":"F₂=F₁×A₂/A₁. Small force on small piston creates large force on large piston (Pascal's Law)."},
  {"subject":"Mechanical","topic":"Fluid Mechanics","stream":"mechanical","difficulty":2,
   "question_text":"Bernoulli's equation: P + ½ρv² + ρgh = constant. It applies to:","options":["Steady, incompressible, non-viscous flow along a streamline","All fluid flows","Compressible gases only","Turbulent flow"],"correct_index":0,"explanation":"Bernoulli's theorem: energy conservation for ideal fluid — applies to steady, inviscid, incompressible flow."},
  {"subject":"Mechanical","topic":"Fluid Mechanics","stream":"mechanical","difficulty":1,
   "question_text":"Hydraulic oil viscosity grade ISO VG 46 means kinematic viscosity of approximately:","options":["46 cSt at 40°C","46 cP at 20°C","46 mm²/s at 100°C","46 SUS at 60°C"],"correct_index":0,"explanation":"ISO VG grade = kinematic viscosity in centistokes (cSt) at 40°C ± 10%."},
  # Bearings & Lubrication
  {"subject":"Mechanical","topic":"Bearings & Lubrication","stream":"mechanical","difficulty":1,
   "question_text":"The bearing suitable for heavy radial loads at low speeds is:","options":["Journal (plain/sleeve) bearing","Ball bearing","Roller bearing","Needle bearing"],"correct_index":0,"explanation":"Journal bearings operate on hydrodynamic oil film — ideal for heavy continuous radial loads (e.g., crankshaft main bearings)."},
  {"subject":"Mechanical","topic":"Bearings & Lubrication","stream":"mechanical","difficulty":2,
   "question_text":"Grease lubrication is preferred over oil in bearings when:","options":["Sealing is difficult, speed is moderate, environment is contaminated","Very high speeds","Continuous lubrication is possible","Heavy loads at very high temperatures"],"correct_index":0,"explanation":"Grease stays in place, provides sealing, and suits moderate-speed bearings where oil retention is difficult."},
  # Thermodynamics & Steam
  {"subject":"Mechanical","topic":"Thermodynamics","stream":"mechanical","difficulty":1,
   "question_text":"In a Carnot cycle, heat is rejected at constant:","options":["Temperature","Pressure","Volume","Entropy"],"correct_index":0,"explanation":"Carnot cycle: isothermal expansion (T_H), adiabatic expansion, isothermal compression (T_C), adiabatic compression."},
  {"subject":"Mechanical","topic":"Thermodynamics","stream":"mechanical","difficulty":2,
   "question_text":"Boiler efficiency is defined as:","options":["Heat utilised by steam / Heat in fuel burned","Steam output / fuel consumed","Steam pressure / heat input","Heat in steam / total heat"],"correct_index":0,"explanation":"Boiler efficiency=(mass of steam × enthalpy rise)/(mass of fuel × calorific value)×100%."},
  {"subject":"Mechanical","topic":"Thermodynamics","stream":"mechanical","difficulty":2,
   "question_text":"An air compressor with intercooling between stages is used to:","options":["Reduce work input and lower discharge temperature","Increase compression ratio in single stage","Reduce volumetric efficiency","Increase air velocity"],"correct_index":0,"explanation":"Intercooling cools air between stages → approaches isothermal compression → less work. Also reduces temperature."},
  # Maintenance & Safety
  {"subject":"Mechanical","topic":"Maintenance & Safety","stream":"mechanical","difficulty":1,
   "question_text":"Preventive Maintenance (PM) is carried out:","options":["At scheduled intervals before failure","Only after equipment breaks down","When spares are available","Once a year only"],"correct_index":0,"explanation":"PM is systematic, scheduled maintenance to prevent failures — includes lubrication, inspection, calibration."},
  {"subject":"Mechanical","topic":"Maintenance & Safety","stream":"mechanical","difficulty":2,
   "question_text":"LOTO (Lockout-Tagout) procedure is used to:","options":["Isolate hazardous energy before maintenance","Log maintenance records","Lubricate equipment","Test tool accuracy"],"correct_index":0,"explanation":"LOTO: energy isolation procedure to protect maintenance workers from unexpected energisation of equipment."},
  {"subject":"Mechanical","topic":"Maintenance & Safety","stream":"mechanical","difficulty":1,
   "question_text":"The correct fire extinguisher type for electrical fires (Class C) is:","options":["CO₂ or Dry Powder","Water","Foam","Sand bucket"],"correct_index":0,"explanation":"CO₂ and dry chemical (ABC powder) are safe for electrical fires — water conducts electricity and should never be used."},
]

# Also create a dedicated ALP CBT2 bank file
def build_bank(questions, exam_key):
    result = []
    seen = set()
    for q in questions:
        key = q["question_text"].strip().lower()[:120]
        if key in seen:
            continue
        seen.add(key)
        subj = q["subject"].replace(" ","_").lower()[:4]
        topic = q["topic"].replace(" ","_").replace("&","n").lower()[:6]
        q["id"] = f"{exam_key}_{subj}_{topic}_{uuid.uuid4().hex[:6]}"
        result.append(q)
    return result

bank = build_bank(ALP_CBT2, "alp_cbt2")
out_path = BANK_DIR / "rrb_alp_cbt2.json"
out_path.write_text(json.dumps(bank, indent=2, ensure_ascii=False))

from collections import Counter
elec = [q for q in bank if q["stream"]=="electrical"]
mech = [q for q in bank if q["stream"]=="mechanical"]
print(f"Total: {len(bank)} questions")
print(f"\nElectrical stream: {len(elec)}")
etopics = Counter(q["topic"] for q in elec)
for t,c in sorted(etopics.items()):
    print(f"  {t}: {c}")
print(f"\nMechanical stream: {len(mech)}")
mtopics = Counter(q["topic"] for q in mech)
for t,c in sorted(mtopics.items()):
    print(f"  {t}: {c}")
