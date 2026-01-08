import httpx
from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse

app = FastAPI(title="Fleet Management Gateway")

# --- KONFIGURASI URL SERVICE INTERNAL ---
# Nama host "vehicle-service" dan "availability-service" diambil dari nama service di docker-compose.yml
VEHICLE_SERVICE_URL = "http://vehicle-service:8000/graphql/"
AVAILABILITY_SERVICE_URL = "http://availability-service:8000/graphql/"

@app.get("/")
def index():
    return {
        "message": "Gateway is Running",
        "endpoints": {
            "vehicle": "/vehicle/graphql/",
            "availability": "/availability/graphql/"
        }
    }

# --- PROXY KE VEHICLE SERVICE ---
# Menangkap method GET (untuk Playground) dan POST (untuk Query/Mutation)
@app.api_route("/vehicle/graphql/", methods=["GET", "POST"])
async def proxy_vehicle(request: Request):
    return await forward_request(request, VEHICLE_SERVICE_URL)

# --- PROXY KE AVAILABILITY SERVICE ---
@app.api_route("/availability/graphql/", methods=["GET", "POST"])
async def proxy_availability(request: Request):
    return await forward_request(request, AVAILABILITY_SERVICE_URL)

# --- FUNGSI PEMBANTU (FORWARDER) ---
async def forward_request(request: Request, target_url: str):
    async with httpx.AsyncClient() as client:
        try:
            # 1. Baca Body, Headers, dan Query Params dari request asli
            body = await request.body()
            params = dict(request.query_params)
            headers = dict(request.headers)

            # Hapus header 'host' dan 'content-length' agar tidak bentrok di tujuan
            headers.pop("host", None)
            headers.pop("content-length", None)

            # 2. Kirim ke Service Tujuan (Internal Docker)
            response = await client.request(
                method=request.method,
                url=target_url,
                content=body,
                headers=headers,
                params=params,
                timeout=30.0 # Timeout agak lama jaga-jaga koneksi lambat
            )

            # 3. Kembalikan jawaban Service ke Pengirim Asli (Ngrok/Frontend)
            return Response(
                content=response.content,
                status_code=response.status_code,
                headers=dict(response.headers),
                media_type=response.headers.get("content-type")
            )
            
        except httpx.RequestError as e:
            return JSONResponse(
                status_code=503, 
                content={"error": f"Service sedang tidak dapat dihubungi: {str(e)}"}
            )