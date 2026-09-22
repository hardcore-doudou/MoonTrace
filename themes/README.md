# MoonTrace Themes

MoonTrace supports local theme overrides without storing personal artwork in the public repository.

Create this directory in your local MoonTrace installation:

```text
user_data/
└─ theme/
   ├─ background.png
   └─ theme.css
```

Supported background filenames:

```text
background.png
background.jpg
background.jpeg
background.webp
```

The background is picked up automatically.

Copy `custom-theme.example.css` to:

```text
user_data/theme/theme.css
```

and edit it to override MoonTrace's colors, overlay, typography, cards, decorations, or other CSS.

`user_data/` is ignored by Git, so local personal themes are not committed or uploaded.

---

## 中文

MoonTrace 支持只保存在本机的主题覆盖，不需要把个人图片上传到公开仓库。

在本地 MoonTrace 目录中创建：

```text
user_data/
└─ theme/
   ├─ background.png
   └─ theme.css
```

背景文件支持：

```text
background.png
background.jpg
background.jpeg
background.webp
```

放进去以后会自动作为背景使用。

可以把 `custom-theme.example.css` 复制到：

```text
user_data/theme/theme.css
```

然后自行修改配色、遮罩、字体、卡片、装饰以及其他 CSS。

`user_data/` 已被 Git 忽略，因此本地个人主题不会被提交或上传。
