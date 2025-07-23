# AI-Based Traffic Management System

A real-time, AI-powered traffic management system that optimizes traffic light timings at a 4-way intersection using vehicle density analysis and SUMO simulation, with a live Pygame visualizer.

---

## Features

- **Realistic 4-way intersection** with multiple vehicle types (cars, buses, bikes, emergency vehicles)
- **AI-based traffic light optimization** using real-time vehicle density and trend analysis
- **Priority handling for emergency vehicles**
- **Pygame visualization** for live monitoring and debugging
- **Configurable SUMO simulation** with custom network and routes

---

## Project Structure

```
miniproject_tms/
├── config/                # SUMO network and route configuration
│   ├── intersection.net.xml
│   ├── routes.rou.xml
│   ├── sumo.sumocfg
├── images/                # Vehicle and traffic asset images
│   ├── Audi.png, bus.png, bike.png, Ambulance.png, etc.
├── src/
│   ├── main.py            # Entry point
│   ├── traffic_simulator.py
│   ├── traffic_optimizer.py
│   ├── density_analyzer.py
│   └── visualizer.py
├── requirements.txt
├── test_system.py
└── README.md
```

---

## Installation

### 1. Clone the Repository

First, clone this repository to your local machine:

```bash
git clone https://github.com/Ajay-puttam/MiniProject_TMS.git
cd miniproject_tms
```



### 2. Install SUMO

- **Windows:** Download and install from [SUMO Downloads](https://sumo.dlr.de/docs/Downloads.php), and add SUMO to your PATH.
- **macOS:**  
  ```bash
  brew install sumo
  ```
- **Linux:**  
  ```bash
  sudo apt-get install sumo sumo-tools sumo-doc
  ```

### 3. Install Python Dependencies

Make sure you have Python 3.7 or higher installed. Then, install the required Python packages:

```bash
pip install -r requirements.txt
```

### 4. Verify Installation

Run the test script to verify your setup:

```bash
python test_system.py
```

---

## Usage

### Start the Visualizer

```bash
python src/main.py
```

#### Command-line Options

- `--mode visual` (default): Run with Pygame visualization
- `--mode headless --duration 3600`: Run without visualization for a set duration
- `--mode interactive`: Step through simulation interactively
- `--config path/to/sumo.sumocfg`: Use a custom SUMO config

---

## Controls (in Visualizer)

- **SPACE**: Step simulation
- **R**: Reset simulation
- **Q**: Quit
- **S**: Toggle auto-step

---

## How It Works

1. **SUMO** simulates traffic at a 4-way intersection.
2. **DensityAnalyzer** monitors vehicle density and trends for each approach.
3. **TrafficOptimizer** uses AI logic to adjust traffic light phases and durations.
4. **Visualizer** displays the intersection, vehicles, and traffic lights in real time.

---

## Vehicle Types

- **Car**: Standard vehicles (multiple images)
- **Bus**
- **Bike**
- **Emergency**: Ambulance, etc. (priority handling)

---

## Assets

Ensure the following images are present in the `images/` directory:
- Audi.png, Black_viper.png, car.png, Mini_truck.png, bus.png, bike.png, Ambulance.png, taxi.png

---

## Troubleshooting

- **SUMO not found:** Ensure SUMO is installed and in your PATH. Try `sumo --version`.
- **Import errors:** Run `pip install -r requirements.txt` and check your Python version (3.7+).
- **Pygame issues:** Install with `pip install pygame`. On Linux, you may need `sudo apt-get install python3-pygame`.

---

## Performance

- **Real-time optimization** with sub-second response times
- **Multiple vehicle types** with different behaviors
- **Emergency vehicle priority** with automatic detection
- **Historical trend analysis** for better predictions

---

## Contributing

Contributions are welcome! Ideas:
- Improve AI/optimization logic
- Add new vehicle types or behaviors
- Enhance visualization or performance

--- 
