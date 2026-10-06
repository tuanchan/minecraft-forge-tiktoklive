import zipfile
z=zipfile.ZipFile('TikTokMobForge/.gradle/mavenizer/repo/net/minecraftforge/forge/26.2-65.1.3/forge-26.2-65.1.3-sources.jar')
s=z.read('net/minecraft/world/entity/Entity.java').decode();a=s.index('public Entity(');print(s[a:a+3000])
