from fastapi import APIRouter, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.routing import APIRoute
from starlette.responses import JSONResponse

from app.modules.research.configuration.service import AIConfiguration, AIInput, AIStatus, ConnectionResult


class PrivateRoute(APIRoute):
    def get_route_handler(self):
        handler = super().get_route_handler()

        async def private(request):
            # Default validation errors echo rejected inputs, including secrets.
            try:
                response = await handler(request)
            except RequestValidationError:
                response = JSONResponse({"detail": "Invalid AI configuration fields"}, status_code=422)
            response.headers["Cache-Control"] = "no-store"
            return response

        return private


def create_router(service: AIConfiguration):
    router = APIRouter(prefix="/api/settings/ai", route_class=PrivateRoute)

    @router.get("", response_model=AIStatus)
    def status():
        return service.status()

    @router.post("", response_model=AIStatus)
    def save(body: AIInput):
        try:
            return service.save(body)
        except ValueError as exc:
            raise HTTPException(422, str(exc)) from None
        except OSError:
            raise HTTPException(503, "Could not persist private AI configuration") from None

    @router.delete("", response_model=AIStatus)
    def reset():
        try:
            return service.reset()
        except OSError:
            raise HTTPException(503, "Could not restore environment configuration") from None

    @router.post("/test", response_model=ConnectionResult)
    def test(body: AIInput):
        try:
            return service.test(body)
        except ValueError as exc:
            raise HTTPException(422, str(exc)) from None

    return router
