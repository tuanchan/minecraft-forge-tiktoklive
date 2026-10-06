import zipfile
from pathlib import Path
z=zipfile.ZipFile('TikTokMobForge/.gradle/mavenizer/repo/net/minecraftforge/forge/26.2-65.1.3/forge-26.2-65.1.3-sources.jar')
for n in ['net/minecraft/client/renderer/entity/state/TextDisplayEntityRenderState.java','net/minecraft/client/renderer/rendertype/RenderTypes.java','net/minecraftforge/client/event/EntityRenderersEvent.java','net/minecraft/client/renderer/entity/EntityRenderDispatcher.java']:
 p=Path('temp/forge-src')/n;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(z.read(n))
