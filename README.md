# 🚗 Fleet Management System (Microservices)

Sistem manajemen penyewaan kendaraan berbasis **Microservices Architecture**. Sistem ini menangani inventaris kendaraan (*Vehicle Service*) dan penjadwalan peminjaman (*Availability Service*), yang disatukan melalui **API Gateway** terpusat.

Sistem ini dibangun untuk memenuhi tugas besar integrasi sistem, mencakup autentikasi JWT, validasi lintas layanan, dan integrasi dengan layanan eksternal.

![Python](https://img.shields.io/badge/Python-3.9-blue?style=for-the-badge&logo=python)
![FastAPI](https://img.shields.io/badge/FastAPI-Gateway-green?style=for-the-badge&logo=fastapi)
![GraphQL](https://img.shields.io/badge/GraphQL-Ariadne-pink?style=for-the-badge&logo=graphql)
![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?style=for-the-badge&logo=docker)

## 🏗️ Architecture Design

Sistem menggunakan pola **API Gateway** sebagai pintu masuk tunggal (Single Entry Point).

```mermaid
graph TD
    User[Client / Frontend / Kelompok Lain] -->|HTTPS Request| Ngrok[Ngrok Tunnel]
    Ngrok -->|Port 4000| Gateway[API Gateway]
    
    subgraph Docker Internal Network
        Gateway -->|/vehicle/graphql/| VS[Vehicle Service]
        Gateway -->|/availability/graphql/| AS[Availability Service]
        
        VS -->|Read/Write| DB1[(Vehicle DB)]
        AS -->|Read/Write| DB2[(Availability DB)]
        
        AS -.->|Internal Request: Cek Fisik Mobil| VS
    end
    
    AS -->|External Request: Validasi User| ExtUser[External User Service]
