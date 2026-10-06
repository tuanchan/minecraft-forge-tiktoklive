import zipfile
z=zipfile.ZipFile('TikTokMobForge/.gradle/mavenizer/repo/net/minecraftforge/forge/26.2-65.1.3/forge-26.2-65.1.3-sources.jar')
s=z.read('net/minecraft/client/renderer/texture/TextureManager.java').decode();a=s.index('public void register(');print(s[a:a+1600])
