# 虫阶 / TaxaQuest

一个看昆虫照片、在分类树上选择分类阶元的猜谜游戏。

- **题库**：以中国境内 iNaturalist 研究级记录为基础，每种一条带地点的记录、一张图。
- **作答**：树形展开 + 中文名 / 拉丁名 / 拼音搜索；可以停在任何有把握的阶元。
- **计分**：目、亚目、科、亚科、属、种六档；总科、下目、族、亚属等保留在树和答案里，但不单独计分。
- **部署**：纯静态站点，适合 GitHub Pages，不需要服务器或数据库。

## 计分规则

| 选择 | 得分 |
|---|---:|
| 目 order | 10 |
| 亚目 suborder | 20 |
| 科 family | 40 |
| 亚科 subfamily | 55 |
| 属 genus | 75 |
| 种 species | 100 |

如果选的是总科、下目、族、亚属等“检索阶元”，按它上方最近的计分阶元计分；如果选错分支，按与正确答案的共同祖先计分后再乘 0.9。

例：目标是日本弓背蚁。

- 选蚁科 → 40
- 选蚁亚科 → 55
- 选弓背蚁属 → 75
- 选日本弓背蚁 → 100
- 选蜜蜂科 → 18（共同祖先细腰亚目 20 × 0.9）
- 选弓背蚁属下的另一种 → 68（属 75 × 0.9）

详细逻辑在 `src/lib/scoring.ts`，单测在 `src/lib/scoring.test.ts`。

## 目录

```text
data/
  raw/          iNaturalist API 原始响应缓存（不提交）
  curated/      选题、单种记录、图片清单
public/
  data/         前端读取的 game.json
  images/       压缩后的 WebP 图片
scripts/        数据抓取与构建脚本
src/            React 前端
```

## 本地运行

```bash
npm install
npm run dev
```

浏览器打开终端输出的本地地址。

构建静态文件：

```bash
npm run build
npm run preview
```

## 重建题库

需要 Python 3.10+、Pillow。所有 iNaturalist 请求都会缓存到 `data/raw/inat/`，重复执行不会重复请求。

```bash
python scripts/01_fetch_user.py       # 抓取 cg1ns3ct 的昆虫记录
python scripts/02_fetch_candidates.py # 中国境内有可用照片的候选种
python scripts/03_select_targets.py   # 分层选目标种
python scripts/04_fetch_records.py    # 每种选一条记录/一张图
python scripts/05_download_images.py  # 下载并压缩为 WebP
python scripts/06_build_game.py       # 分类树 + game.json
python scripts/07_validate.py         # 数据校验
python scripts/08_credits.py          # 生成 CREDITS.md
```

## GitHub Pages 部署

1. 在 GitHub 新建**公开**仓库，例如 `insect-taxa-game`。
2. 本地添加 remote 并推送：

   ```bash
   git remote add origin https://github.com/<你的用户名>/insect-taxa-game.git
   git push -u origin main
   ```

3. 仓库 **Settings → Pages → Build and deployment → Source** 选择 **GitHub Actions**。
4. 推送到 `main` 后，`.github/workflows/deploy.yml` 会自动构建并发布。
5. 页面地址通常是：

   ```text
   https://<你的用户名>.github.io/insect-taxa-game/
   ```

GitHub Pages 免费账号使用公开仓库最简单；单站点约 1GB，当前图片总量远低于这个限制。

## 图片许可

只使用以下许可：

- CC0
- CC BY
- CC BY-SA
- CC BY-NC
- CC BY-NC-SA

不使用 ND（禁止演绎）和 all rights reserved。每张图的作者、许可和原观察记录都保存在 `CREDITS.md`，页面上也会显示。

`public/images/` 下的图片**不**适用代码的 MIT 许可；它们分别适用原 iNaturalist 图片许可。

## 数据说明

- 分类骨架来自 iNaturalist 当前分类快照；蚁科按现行安排放在蚁总科 Formicoidea，旧分类常置于胡蜂总科，答案页会保留完整路径。
- 目标种优先采用 cg1ns3ct 自有记录；其余优先用中国境内研究级社区记录补足。
- 首批中有部分物种的中国境内可用照片不足，使用了境外同种记录；页面会标注“境外同种记录”，地点按原记录显示，后续可逐步替换为中国影像。
- 卵鞘、虫瘿、潜叶等“昆虫衍生物”记录暂不进入主线，之后可作为彩蛋模式。
- iNaturalist 中文常用名覆盖率不稳定；目标种缺中文名时会回退拉丁名，后续人工补。
- 分类树是分类快照，不是永恒真理；争议类群和异名需要人工复核。

## 技术栈

React 19 + TypeScript + Vite。题库预生成成静态 JSON，图片懒加载；构建产物可直接托管到 GitHub Pages。
