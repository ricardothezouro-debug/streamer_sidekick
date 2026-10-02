# Design do Streamer Sidekick (Sidekick OS)

A fonte da verdade é o [`DESIGN.md`](../../DESIGN.md), na raiz do projeto. Esta pasta guarda a leitura visual dele.

- `sidekick-os-manual-v1.1.pdf`: manual de identidade (cores, tipografia, forma, componentes, ícones, telas de aplicação).
- `tools/sidekick_icons.py`: os dois conjuntos de ícones, `icon-ui` (linha HUD, grade 24) e `icon-brand` (pixel 12×12). É daqui que a implementação no app parte.
- `tools/manual.py`: gera o manual a partir dos tokens.

## Gerar o manual

As fontes Chakra Petch, IBM Plex Sans, IBM Plex Mono e VT323 (licença OFL, Google Fonts) precisam estar em
`src/streamer_sidekick/assets/fonts/` ou numa pasta apontada pela variável `SIDEKICK_FONTS`.

```bash
python docs/design/tools/manual.py pdf docs/design/sidekick-os-manual-v1.1.pdf
```

Para revisar páginas como imagem: `python docs/design/tools/manual.py png <pasta> 13 14`.
