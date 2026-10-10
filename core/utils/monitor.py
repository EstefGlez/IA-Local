"""Módulo de monitoreo de recursos del sistema (CPU, RAM)."""

import threading
import time
from contextlib import contextmanager
from typing import List, Tuple, Optional

try:
    import psutil
except ImportError:
    psutil = None

try:
    import matplotlib
    matplotlib.use("Agg")  # Backend sin GUI
    import matplotlib.pyplot as plt
except ImportError:
    plt = None


class ResourceMonitor:
    """Monitor de recursos que muestrea CPU y RAM en un hilo separado."""

    def __init__(self, interval: float = 0.5):
        """
        Inicializa el monitor.

        Args:
            interval: Intervalo de muestreo en segundos (default 0.5s)
        """
        self.interval = interval
        self._samples: List[Tuple[float, float, float]] = []  # (timestamp, cpu%, ram%)
        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self._start_time: Optional[float] = None

    def _sample_loop(self):
        """Bucle de muestreo que corre en hilo secundario."""
        process = psutil.Process()
        while not self._stop_event.is_set():
            timestamp = time.time() - self._start_time
            cpu_percent = process.cpu_percent(interval=None)
            ram_percent = process.memory_percent()
            self._samples.append((timestamp, cpu_percent, ram_percent))
            time.sleep(self.interval)

    def start(self):
        """Inicia el muestreo."""
        if psutil is None:
            raise RuntimeError("psutil no está instalado. Ejecuta: pip install psutil")
        self._samples.clear()
        self._stop_event.clear()
        self._start_time = time.time()
        # Primera llamada para inicializar cpu_percent
        psutil.Process().cpu_percent(interval=None)
        self._thread = threading.Thread(target=self._sample_loop, daemon=True)
        self._thread.start()

    def stop(self) -> List[Tuple[float, float, float]]:
        """
        Detiene el muestreo y devuelve las muestras recopiladas.

        Returns:
            Lista de tuplas (timestamp, cpu%, ram%)
        """
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=2.0)
        return self._samples

    def plot(
        self,
        output_path: str = "performance_dashboard.png",
        all_samples: Optional[List[Tuple[float, float, float]]] = None,
        session_start_time: Optional[float] = None,
    ):
        """
        Genera y guarda la gráfica de evolución de recursos.

        Args:
            output_path: Ruta donde guardar la imagen
            all_samples: Muestras acumuladas de toda la sesión (opcional). Si se proporciona,
                         se usan estas en lugar de self._samples para gráfica acumulativa.
            session_start_time: Timestamp de inicio de la sesión (para ejes correctos en gráfica acumulativa).
        """
        if plt is None:
            raise RuntimeError("matplotlib no está instalado. Ejecuta: pip install matplotlib")

        # Usar muestras acumuladas si se proporcionan, sino las de esta inferencia
        samples_to_plot = all_samples if all_samples is not None else self._samples
        if not samples_to_plot:
            return

        # Determinar timestamps para el eje X
        if all_samples is not None and session_start_time is not None:
            # Timestamps absolutos desde inicio de sesión
            timestamps = [s[0] for s in samples_to_plot]
            xlabel = "Tiempo desde inicio de sesión (segundos)"
            title = "Uso de Recursos - Sesión Completa"
        else:
            # Timestamps relativos a esta inferencia
            timestamps = [s[0] for s in samples_to_plot]
            xlabel = "Tiempo (segundos)"
            title = "Uso de Recursos Durante Inferencia"

        cpu_values = [s[1] for s in samples_to_plot]
        ram_values = [s[2] for s in samples_to_plot]

        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 7), sharex=True)
        fig.suptitle(title, fontsize=14, fontweight="bold")

        # CPU
        ax1.plot(timestamps, cpu_values, color="#2E86C1", linewidth=1.5)
        ax1.fill_between(timestamps, cpu_values, alpha=0.2, color="#2E86C1")
        ax1.set_ylabel("CPU %", fontsize=11)
        ax1.set_ylim(0, max(max(cpu_values) * 1.2, 10))
        ax1.grid(True, alpha=0.3)
        ax1.set_title("Uso de CPU", fontsize=11)

        # RAM
        ax2.plot(timestamps, ram_values, color="#E74C3C", linewidth=1.5)
        ax2.fill_between(timestamps, ram_values, alpha=0.2, color="#E74C3C")
        ax2.set_ylabel("RAM %", fontsize=11)
        ax2.set_xlabel(xlabel, fontsize=11)
        ax2.set_ylim(0, max(max(ram_values) * 1.2, 5))
        ax2.grid(True, alpha=0.3)
        ax2.set_title("Uso de RAM", fontsize=11)

        plt.tight_layout()
        plt.savefig(output_path, dpi=150, bbox_inches="tight")
        plt.close(fig)


@contextmanager
def monitor_resources(
    interval: float = 0.5,
    output_path: str = "performance_dashboard.png",
    all_samples: Optional[List[Tuple[float, float, float]]] = None,
    session_start_time: Optional[float] = None,
):
    """
    Context manager para monitorear recursos durante un bloque de código.

    Args:
        interval: Intervalo de muestreo en segundos
        output_path: Ruta donde guardar la gráfica generada
        all_samples: Muestras acumuladas de toda la sesión (opcional). Si se proporciona,
                     el monitor las extenderá con las nuevas muestras y generará gráfica acumulativa.
        session_start_time: Timestamp de inicio de la sesión (para timestamps absolutos en gráfica acumulativa).

    Yields:
        ResourceMonitor: Instancia del monitor para acceso a datos en bruto

    Example:
        with monitor_resources() as monitor:
            # código a medir
            resultado = funcion_costosa()
        # Al salir, se genera performance_dashboard.png
    """
    monitor = ResourceMonitor(interval=interval)
    monitor.start()
    try:
        yield monitor
    finally:
        new_samples = monitor.stop()
        # Si hay muestras acumuladas, extenderlas con las nuevas (ajustando timestamps)
        if all_samples is not None and session_start_time is not None:
            # Las nuevas muestras tienen timestamps relativos a esta inferencia
            # Convertirlas a timestamps absolutos desde session_start_time
            current_time = time.time()
            elapsed_since_session_start = current_time - session_start_time
            # El timestamp de la primera muestra nueva es ~0 (inicio de esta inferencia)
            # Sumamos el offset para que sea absoluto
            adjusted_new_samples = [
                (elapsed_since_session_start - (new_samples[-1][0] - s[0]) if new_samples else elapsed_since_session_start, s[1], s[2])
                for s in new_samples
            ]
            # Más simple: el timestamp 0 de new_samples corresponde a ahora - elapsed_since_session_start
            # offset = tiempo actual - tiempo de la última muestra
            if new_samples:
                last_sample_relative = new_samples[-1][0]  # duracion total de esta inferencia
                offset = elapsed_since_session_start - last_sample_relative
                adjusted_new_samples = [(s[0] + offset, s[1], s[2]) for s in new_samples]
                all_samples.extend(adjusted_new_samples)
            # Generar gráfica con todas las muestras acumuladas
            monitor.plot(output_path, all_samples=all_samples, session_start_time=session_start_time)
        else:
            monitor.plot(output_path)


if __name__ == "__main__":
    # Prueba rápida
    import time
    print("Probando monitor de recursos...")
    with monitor_resources(interval=0.2, output_path="test_dashboard.png"):
        time.sleep(1)
        # Simular carga
        _ = [i ** 2 for i in range(100000)]
    print("Gráfica guardada en test_dashboard.png")