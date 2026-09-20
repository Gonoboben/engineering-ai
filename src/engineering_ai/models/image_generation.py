"""Provider-neutral image-generation protocol for Gate 025.

The image generator is a replaceable provider. It receives only a bounded text
prompt plus explicit raster dimensions/seed and returns image bytes. It owns no
tools, filesystem paths, Supervisor policy, approvals, or publication authority.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol


@dataclass(frozen=True)
class ImageGenerationProviderRequest:
    model: str
    prompt: str
    width: int
    height: int
    seed: int

    def __post_init__(self) -> None:
        model = self.model.strip()
        prompt = self.prompt.strip()
        if not model or len(model) > 256:
            raise ValueError("image generation model must contain 1..256 characters")
        if not prompt or len(prompt) > 12000:
            raise ValueError("image generation prompt must contain 1..12000 characters")
        if self.width < 64 or self.width > 2048 or self.width % 8:
            raise ValueError("image generation width must be 64..2048 and divisible by 8")
        if self.height < 64 or self.height > 2048 or self.height % 8:
            raise ValueError("image generation height must be 64..2048 and divisible by 8")
        if self.seed < 0 or self.seed > 2**31 - 1:
            raise ValueError("image generation seed must be in [0, 2^31-1]")
        object.__setattr__(self, "model", model)
        object.__setattr__(self, "prompt", prompt)


@dataclass(frozen=True)
class ImageGenerationProviderResponse:
    provider: str
    model: str
    media_type: str
    data: bytes = field(repr=False)

    def __post_init__(self) -> None:
        provider = self.provider.strip()
        model = self.model.strip()
        if not provider or len(provider) > 128:
            raise ValueError("image generation provider must contain 1..128 characters")
        if not model or len(model) > 256:
            raise ValueError("image generation response model must contain 1..256 characters")
        if self.media_type != "image/png":
            raise ValueError("Gate 025 provider response media type must be image/png")
        if not isinstance(self.data, bytes) or not self.data:
            raise ValueError("image generation response data must be non-empty bytes")
        object.__setattr__(self, "provider", provider)
        object.__setattr__(self, "model", model)


class ImageGenerationProvider(Protocol):
    provider_name: str

    def generate(
        self,
        request: ImageGenerationProviderRequest,
        *,
        timeout_seconds: float = 300.0,
    ) -> ImageGenerationProviderResponse: ...
