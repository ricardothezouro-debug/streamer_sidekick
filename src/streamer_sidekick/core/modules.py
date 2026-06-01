from dataclasses import dataclass


@dataclass(frozen=True)
class ModuleInfo:
    module_id: str
    title: str
    subtitle: str
    status: str
    accent: str


class ModuleRegistry:
    def __init__(self) -> None:
        self._modules: dict[str, ModuleInfo] = {}

    def register(self, module: ModuleInfo) -> None:
        self._modules[module.module_id] = module

    def all(self) -> list[ModuleInfo]:
        return list(self._modules.values())

    def get(self, module_id: str) -> ModuleInfo:
        return self._modules[module_id]
