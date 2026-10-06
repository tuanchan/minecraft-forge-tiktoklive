from pathlib import Path
p=Path('TikTokMobForge/web/app.js');s=p.read_text(encoding='utf-8').replace('phần thưởngTarget','mobTarget').replace('phần thưởng_target','mob_target').replace('Tìm phần thưởng, vật phẩm','Tìm mob, vật phẩm');p.write_text(s,encoding='utf-8')
