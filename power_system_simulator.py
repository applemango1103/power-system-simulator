import math
import tkinter as tk
from tkinter import ttk
from PIL import Image, ImageTk
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
from ttkthemes import ThemedTk
import random

def calculate_power_factor(voltage, impedance_real, impedance_imag, excitation_current):
    compensated_impedance_imag = impedance_imag - excitation_current * 2
    impedance_magnitude = math.sqrt(impedance_real**2 + compensated_impedance_imag**2)
    current = voltage / impedance_magnitude if impedance_magnitude > 0 else 0
    angle = math.degrees(math.atan2(compensated_impedance_imag, impedance_real))
    real_power = voltage * current * math.cos(math.radians(angle))
    apparent_power = voltage * current
    reactive_power = voltage * current * math.sin(math.radians(angle))
    power_factor = real_power / apparent_power if apparent_power > 0 else 0
    return current, max(0, min(power_factor, 1)), angle, real_power, apparent_power, reactive_power

class RotaryDial(tk.Canvas):
    def __init__(self, parent, min_val, max_val, initial_val, label, callback, step=0.5):
        super().__init__(parent, width=200, height=200, bg="#eef2f3")
        self.min_val = min_val
        self.max_val = max_val
        self.value = initial_val
        self.label = label
        self.callback = callback
        self.step = step

        self.angle = (self.value - self.min_val) / (self.max_val - self.min_val) * 360
        self.draw_dial()
        self.bind("<B1-Motion>", self.on_drag)

    def draw_dial(self):
        self.delete("all")
        self.create_oval(20, 20, 180, 180, outline="black", width=2)

        for i in range(12):
            angle = math.radians(i * 30 - 90)
            x_start = 100 + 70 * math.cos(angle)
            y_start = 100 + 70 * math.sin(angle)
            x_end = 100 + 80 * math.cos(angle)
            y_end = 100 + 80 * math.sin(angle)
            self.create_line(x_start, y_start, x_end, y_end, fill="black", width=1)

        pointer_angle = math.radians(self.angle - 90)
        pointer_x = 100 + 70 * math.cos(pointer_angle)
        pointer_y = 100 + 70 * math.sin(pointer_angle)
        self.create_line(100, 100, pointer_x, pointer_y, fill="red", width=3)
        self.create_oval(pointer_x - 5, pointer_y - 5, pointer_x + 5, pointer_y + 5, fill="red")

        self.create_text(100, 100, text=f"{self.value:.1f}", font=("Arial", 14))
        self.create_text(100, 180, text=self.label, font=("Arial", 10))

    def on_drag(self, event):
        dx = event.x - 100
        dy = event.y - 100
        angle = math.atan2(dy, dx)
        degrees = (math.degrees(angle) + 450) % 360
        self.angle = degrees

        raw_value = self.min_val + (self.max_val - self.min_val) * (self.angle / 360)
        self.value = round(raw_value / self.step) * self.step
        self.value = max(self.min_val, min(self.max_val, self.value))
        self.draw_dial()
        self.callback()

class PowerSystemSimulator:
    def __init__(self, root):
        self.root = root
        self.root.title("Dynamic Power System Simulator with Synchronous Condenser")
        self.voltage = 230
        self.impedance_real = 5
        self.impedance_imag = 5
        self.excitation_current = 0
        self.power_factor_history = []
        self.dynamic_mode = False
        self.setup_ui()

    def setup_ui(self):
        self.control_frame = tk.Frame(self.root, bg="#eef2f3")
        self.control_frame.pack(side=tk.LEFT, padx=10, pady=10)

        self.real_impedance_dial = RotaryDial(
            self.control_frame,
            min_val=1,
            max_val=20,
            initial_val=self.impedance_real,
            label="Real Impedance",
            callback=self.update_simulation,
        )
        self.real_impedance_dial.pack(pady=10)

        self.imag_impedance_dial = RotaryDial(
            self.control_frame,
            min_val=1,
            max_val=20,
            initial_val=self.impedance_imag,
            label="Imaginary Impedance",
            callback=self.update_simulation,
        )
        self.imag_impedance_dial.pack(pady=10)

        self.excitation_dial = RotaryDial(
            self.control_frame,
            min_val=0,
            max_val=10,
            initial_val=self.excitation_current,
            label="Excitation Current",
            callback=self.update_simulation,
            step=0.5,
        )
        self.excitation_dial.pack(pady=10)

        tk.Button(
            self.control_frame,
            text="Static Mode",
            command=self.set_static_mode,
            bg="#d1e7dd",
            font=("Arial", 10),
        ).pack(pady=5)

        tk.Button(
            self.control_frame,
            text="Dynamic Mode",
            command=self.set_dynamic_mode,
            bg="#ffedd5",
            font=("Arial", 10),
        ).pack(pady=5)

        self.vector_canvas = tk.Canvas(self.root, width=400, height=400, bg="#dff9fb")
        self.vector_canvas.pack(side=tk.LEFT, padx=10, pady=10)

        self.image_panel = tk.Label(self.vector_canvas, bg="#dff9fb")
        self.image_panel.place(relx=0.5, rely=0.5, anchor=tk.CENTER)

        self.status_frame = tk.Frame(self.root, bg="#f0f0f0")
        self.status_frame.pack(side=tk.RIGHT, padx=10, pady=10, fill=tk.BOTH, expand=True)

        self.status_display = tk.Text(self.status_frame, height=15, width=40, state="disabled", font=("Arial", 10))
        self.status_display.pack()

        self.setup_plot()
        self.load_synchronous_condenser_image()

    def setup_plot(self):
        self.fig = Figure(figsize=(10, 5), dpi=100)
        self.ax_vector = self.fig.add_subplot(121)
        self.ax_vector.set_title("Voltage-Current Vector Diagram")
        self.ax_vector.set_xlim(-250, 250)
        self.ax_vector.set_ylim(-250, 250)

        self.ax_pf = self.fig.add_subplot(122)
        self.ax_pf.set_title("Power Factor Over Time")
        self.ax_pf.set_ylim(0.8, 1)

        self.canvas = FigureCanvasTkAgg(self.fig, master=self.status_frame)
        self.canvas.get_tk_widget().pack()

    def load_synchronous_condenser_image(self):
        try:
            image_path = "C:/Users/Jaewook Lee/Downloads/synchronous condenser.png"
            image = Image.open(image_path)
            image = image.resize((400, 400), Image.Resampling.LANCZOS)
            self.photo = ImageTk.PhotoImage(image)  # self.photo를 인스턴스 속성으로 유지
            self.image_panel.config(image=self.photo)
            self.image_panel.image = self.photo  # 참조를 유지하여 삭제 방지
        except FileNotFoundError:
            self.image_panel.config(text="Image not found", font=("Arial", 10), fg="red")
        except Exception as e:
            print(f"Error loading image: {e}")
            self.image_panel.config(text="Error loading image", font=("Arial", 10), fg="red")


    def set_static_mode(self):
        self.dynamic_mode = False

    def set_dynamic_mode(self):
        self.dynamic_mode = True
        self.simulate_dynamic_load()

    def simulate_dynamic_load(self):
        if self.dynamic_mode:
            self.real_impedance_dial.value *= random.uniform(0.95, 1.05)
            self.imag_impedance_dial.value *= random.uniform(0.95, 1.05)
            self.real_impedance_dial.draw_dial()
            self.imag_impedance_dial.draw_dial()
            self.update_simulation()
            self.root.after(2000, self.simulate_dynamic_load)

    def update_simulation(self):
        self.impedance_real = self.real_impedance_dial.value
        self.impedance_imag = self.imag_impedance_dial.value
        self.excitation_current = self.excitation_dial.value

        current, power_factor, angle, real_power, apparent_power, reactive_power = calculate_power_factor(
            self.voltage, self.impedance_real, self.impedance_imag, self.excitation_current
        )

        self.power_factor_history.append(power_factor)
        self.update_status(real_power, apparent_power, reactive_power, power_factor, angle, current)
        self.update_plot(angle, current)

    def update_status(self, real_power, apparent_power, reactive_power, power_factor, angle, current):
        self.status_display.config(state="normal")
        self.status_display.delete(1.0, tk.END)
        self.status_display.insert(
            tk.END,
            f"Voltage: {self.voltage} V\n"
            f"Real Power: {real_power:.2f} kW\nApparent Power: {apparent_power:.2f} kVA\n"
            f"Reactive Power: {reactive_power:.2f} kVAR\nPower Factor: {power_factor:.2f}\n"
            f"Phase Angle: {angle:.2f} \xb0\nCurrent: {current:.2f} A\n",
        )

        if power_factor < 0.95:
            if reactive_power > 0:
                self.status_display.insert(tk.END, "\n\u26a0 Low Power Factor (Lagging Load)! Increase Excitation Current to Improve.\n")
            elif reactive_power < 0:
                self.status_display.insert(tk.END, "\n\u26a0 Low Power Factor (Leading Load)! Decrease Excitation Current to Improve.\n")
        elif power_factor > 0.98:
            self.status_display.insert(tk.END, "\n\u26a0 High Power Factor! Adjust Excitation Current for Stability.\n")
        elif 0.95 <= power_factor <= 0.98:
            self.status_display.insert(tk.END, "\n\u2705 Power Factor is Stable.\n")

        self.status_display.config(state="disabled")

    def update_plot(self, angle, current):
        self.ax_vector.clear()
        self.ax_vector.set_title("Voltage-Current Vector Diagram")
        self.ax_vector.set_xlim(-250, 250)
        self.ax_vector.set_ylim(-250, 250)

        voltage_x = self.voltage
        current_x = voltage_x * math.cos(math.radians(angle))
        current_y = voltage_x * math.sin(math.radians(angle))

        self.ax_vector.quiver(0, 0, voltage_x, 0, angles='xy', scale_units='xy', scale=1, color='blue', label='Voltage')
        self.ax_vector.quiver(0, 0, current_x, current_y, angles='xy', scale_units='xy', scale=1, color='red', label='Current')
        self.ax_vector.legend()

        self.ax_pf.clear()
        self.ax_pf.set_title("Power Factor Over Time")
        self.ax_pf.plot(self.power_factor_history, linestyle='-', color='orange', label='Power Factor')
        self.ax_pf.legend()

        self.canvas.draw()

if __name__ == "__main__":
    root = ThemedTk(theme="arc")
    simulator = PowerSystemSimulator(root)
    root.mainloop()
