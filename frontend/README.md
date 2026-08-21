# Casino Prestige PWA - POS & KDS Frontend
==========================================

Este directorio contiene la interfaz web progresiva (PWA) de cara a sala y producción, optimizada para pantallas táctiles y empaquetada de manera ligera utilizando **Tailwind CSS**.

## Módulos de Interfaz

1. **`pos.html` (Comandero de Meseros / Autoservicio QR)**:
   - Permite a los meseros (o clientes escaneando un código QR) registrar comandas.
   - Si se escanea un código QR del slot, captura automáticamente el parámetro `?machine_id=UUID` para asociar la comanda al tragamonedas respectivo.
   - Contiene selector de categorías dinámico y rejilla de productos cargada directamente desde la base de datos relacional.
   - Carrito con nota de preparación e inicio de sesión modal JWT.

2. **`kds.html` (Kitchen Display System)**:
   - Panel de control para operarios de Cocina y Barra.
   - Selector de estación al inicio para segregar las comandas correspondientes.
   - Conexión persistente mediante WebSocket a `/ws/kds?station=...` con lógica de reconexión exponencial.
   - Visualización de tarjetas FIFO interactivas para mover estados (`Preparar` -> `Terminar` -> `Entregar`).

## Service Worker e Instalación PWA

- **`manifest.json`**: Define el diseño del icono, comportamiento de la app independiente (`standalone`) y paleta visual Obsidian & Gold.
- **`sw.js`**: Implementa Service Worker para el almacenamiento en caché offline, permitiendo que la aplicación se instale en tablets Android/iOS de forma nativa.
