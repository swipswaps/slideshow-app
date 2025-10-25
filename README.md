# 📸 Slideshow Manager

A professional-grade GUI application for managing images and creating MP4 slideshows with advanced features.

## ✨ Features

- **📷 Thumbnail Preview** - Visual preview of all images with 100x100px thumbnails
- **🔍 Search & Filter** - Real-time search by filename
- **📊 Sort Options** - Sort by name, date modified, or file size
- **✏️ Rename** - Rename images directly from the GUI
- **👁️ Hide/Show** - Toggle images on/off (persisted in config)
- **🗑️ Remove** - Delete images permanently
- **➕ Add** - Import images via file dialog
- **🎬 Create Slideshow** - Generate MP4 videos from visible images
- **📈 Statistics** - Real-time stats on total, visible, hidden images and total size
- **🔄 Auto-Dependency Management** - Automatically detects and installs ffmpeg

## 🚀 Quick Start

### One-Time Setup

```bash
bash setup.sh
```

This will:
- Install Python dependencies (Pillow)
- Detect and install ffmpeg if needed
- Verify all requirements

### Run the Application

```bash
python3 slideshow_manager.py
```

## 📖 Usage Guide

### Adding Images

1. Click **➕ Add Images** button
2. Select one or more image files (JPG, PNG)
3. Images appear in the list with thumbnails

### Organizing Images

- **Search**: Type in the search box to filter images by filename
- **Sort**: Choose sort order (name, date modified, file size)
- **Rename**: Click ✏️ Rename to change image filename
- **Hide**: Click 👁️ Hide to exclude from slideshow (marked 🚫 HIDDEN)
- **Show**: Click 👁️ Show to include in slideshow (marked ✅ INCLUDED)
- **Remove**: Click 🗑️ Remove to permanently delete

### Creating a Slideshow

1. Organize and hide unwanted images
2. Click **🎬 Create Slideshow**
3. Enter a filename (or use default: `slideshow_YYYYMMDD_HHMMSS.mp4`)
4. Wait for processing to complete
5. MP4 file is saved in the current directory

### Slideshow Settings

- **Frame Rate**: 1 frame per 5 seconds (adjustable in code)
- **Resolution**: 1920x1080 (Full HD)
- **Codec**: H.264 (libx264)
- **Format**: MP4 (yuv420p)
- **Duration**: ~5 seconds per image

## 📊 Statistics Panel

Shows real-time information:
- **Total**: Total number of images found
- **Visible**: Images included in slideshow
- **Hidden**: Images excluded from slideshow
- **Size**: Total disk space used by all images

## ⚙️ Configuration

Hidden images are saved to `.slideshow_config.json`:

```json
{
  "hidden": [
    "/full/path/to/image1.jpg",
    "/full/path/to/image2.jpg"
  ]
}
```

## 🔧 System Requirements

- **Python 3.7+**
- **Pillow** (PIL) - for image processing
- **ffmpeg** - for video creation
- **Tkinter** - usually included with Python

### Supported Operating Systems

- ✅ macOS (with Homebrew)
- ✅ Linux (Debian/Ubuntu, RedHat/CentOS, Arch)
- ✅ Windows (with Chocolatey)

## 🐛 Troubleshooting

### "No visible images to create slideshow"

**Solution**: Click 👁️ Show on hidden images to include them in the slideshow.

### "Too Few Images"

**Solution**: You need at least 2 images to create a slideshow.

### ffmpeg not found

**Solution**: Run `bash setup.sh` to install ffmpeg automatically.

### Images not loading

**Solution**: 
- Ensure images are in JPG or PNG format
- Check file permissions
- Click 🔄 Refresh to reload

## 📝 Keyboard Shortcuts

- **Scroll**: Mouse wheel or arrow keys
- **Search**: Type in search box (real-time filtering)
- **Sort**: Select from dropdown menu

## 🎨 UI Improvements

- **Status Bar**: Real-time feedback on all operations
- **Statistics Panel**: Live image count and size information
- **Empty State**: Helpful message when no images found
- **Progress Feedback**: Clear indication when creating slideshow
- **Emoji Icons**: Visual indicators for all actions
- **Color Coding**: Green (included), Orange (hidden), Red (errors)

## 📦 Dependencies

```
Pillow>=9.0.0
ffmpeg (system package)
```

## 📄 License

Free to use and modify.

## 💡 Tips

1. **Organize First**: Use search and sort to find images quickly
2. **Preview**: Thumbnails help identify images before including
3. **Batch Operations**: Hide multiple images at once
4. **Backup**: Keep original images safe before removing
5. **Naming**: Use descriptive names for easy searching

## 🔗 Resources

- [Pillow Documentation](https://pillow.readthedocs.io/)
- [FFmpeg Documentation](https://ffmpeg.org/documentation.html)
- [Tkinter Documentation](https://docs.python.org/3/library/tkinter.html)

---

**Made with ❤️ for image enthusiasts**

