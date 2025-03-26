# chronosaaa
this is the main project in my company


1. **Instalar as dependências necessárias**:
    ```sh
    pip install -r requirements.txt
    ```

2. **Configurar o webhook na Meta**:
    - Vá para o console do Facebook Developers e configure a WhatsApp Cloud API.
    - Defina a URL do webhook para apontar para o seu servidor Flask (por exemplo, `http://your-server-ip:5000/webhook`).

3. **Executar o servidor Flask**:
    ```sh
    python chronosai/run.py
    ```
