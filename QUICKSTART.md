# 🚀 Quick Start Guide

Get the Slideshow Manager up and running in 2 minutes!

## Step 1: Install Dependencies (One-time)

```bash
bash setup.sh
```

This automatically:
- ✅ Installs Python dependencies (Pillow)
- ✅ Detects and installs ffmpeg
- ✅ Verifies everything is working

## Step 2: Run the Application

```bash
python3 slideshow_manager.py
```

The GUI window will open. You're ready to go!

---

## 📸 Basic Workflow

### 1. Add Images
- Click **➕ Add Images**
- Select JPG or PNG files
- Images appear with thumbnails

### 2. Organize
- **Search**: Type to filter images
- **Sort**: Choose by name, date, or size
- **Rename**: Click ✏️ to rename
- **Hide**: Click 👁️ to exclude from slideshow

### 3. Create Slideshow
- Click **🎬 Create Slideshow**
- Enter filename (or use default)
- Wait for processing
- MP4 file is ready!

---

## 🎬 Example: Create Your First Slideshow

```bash
# 1. Copy some images to the scripts folder
cp ~/Pictures/*.jpg .

# 2. Run the app
python3 slideshow_manager.py

# 3. In the GUI:
#    - Click "Add Images" (or images auto-load)
#    - Click "Create Slideshow"
#    - Enter name: "my_slideshow.mp4"
#    - Wait for completion

# 4. Play the video
ffplay my_slideshow.mp4
# or
vlc my_slideshow.mp4
```

---

## 🎨 UI Overview

```
┌─────────────────────────────────────────────────────┐
│ 📸 Slideshow Manager                                │
├─────────────────────────────────────────────────────┤
│ ➕ Add Images  🔄 Refresh  Sort: [name ▼]  Search: [___]  🎬 Create Slideshow │
├─────────────────────────────────────────────────────┤
│ Statistics: Total: 5 | Visible: 4 | Hidden: 1 | Size: 12.5 MB │
├─────────────────────────────────────────────────────┤
│                                                     │
│  [Thumbnail] image1.jpg                             │
│              📊 2.5 MB | 📅 2024-10-25 12:30        │
│              ✅ INCLUDED                            │
│              [✏️ Rename] [👁️ Hide] [🗑️ Remove]     │
│                                                     │
│  [Thumbnail] image2.jpg                             │
│              📊 3.1 MB | 📅 2024-10-25 12:25        │
│              🚫 HIDDEN                              │
│              [✏️ Rename] [👁️ Show] [🗑️ Remove]     │
│                                                     │
├─────────────────────────────────────────────────────┤
│ ✅ Slideshow created: my_slideshow.mp4              │
└─────────────────────────────────────────────────────┘
```

---

## ⚡ Keyboard Tips

- **Scroll**: Use mouse wheel to scroll through images
- **Search**: Type in search box for real-time filtering
- **Sort**: Click dropdown to change sort order

---

## 🆘 Troubleshooting

### "No visible images to create slideshow"
→ Click 👁️ Show on hidden images

### "Too Few Images"
→ You need at least 2 images

### ffmpeg not found
→ Run `bash setup.sh` again

### Images not showing
→ Click 🔄 Refresh

---

## 📊 Slideshow Settings

Default settings (can be customized in code):
- **Frame Rate**: 1 frame per 5 seconds
- **Resolution**: 1920x1080 (Full HD)
- **Codec**: H.264
- **Format**: MP4

---

## 💾 Configuration

Hidden images are saved to `.slideshow_config.json`:
- Automatically created on first use
- Persists your hide/show preferences
- Safe to delete (will be recreated)

---

## 🎯 Common Tasks

### Hide all images except one
1. Click 👁️ Hide on all images
2. Click 👁️ Show on the one you want
3. Create slideshow

### Rename multiple images
1. Click ✏️ Rename on each image
2. Enter new name
3. Repeat

### Sort by newest first
1. Click Sort dropdown
2. Select "date modified"
3. Images sort newest first

### Search for specific images
1. Type in Search box
2. Results filter in real-time
3. Clear search to see all

---

## 📝 File Formats Supported

- ✅ JPG / JPEG
- ✅ PNG
- ❌ GIF (not supported)
- ❌ WebP (not supported)

---

## 🔗 Next Steps

- Read [README.md](README.md) for detailed documentation
- Check [UX_IMPROVEMENTS.md](UX_IMPROVEMENTS.md) for design details
- Explore the code in `slideshow_manager.py`

---

**Happy slideshow creating! 🎬✨**

