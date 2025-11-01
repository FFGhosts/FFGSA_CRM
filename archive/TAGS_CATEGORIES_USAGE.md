# Tags and Categories Usage Guide

## Overview
Tags and Categories provide two complementary ways to organize your videos and playlists in PiCMS:

- **Tags**: Flexible, ad-hoc labels for quick categorization (e.g., "Holiday", "Featured", "New")
- **Categories**: Structured, hierarchical organization for formal classification (e.g., "Marketing > Social Media")

## Where to Use Tags and Categories

### 1. **Video Upload**
When uploading a new video:
1. Go to **Videos** page
2. Click **Upload Video**
3. Fill in title and description
4. **Select Tags**: Hold Ctrl/Cmd to select multiple tags
5. **Select Categories**: Hold Ctrl/Cmd to select multiple categories
6. Choose your video file and upload

### 2. **Playlist Creation**
When creating a playlist:
1. Go to **Playlists** > **Create Playlist**
2. Enter name and description
3. **Select Tags**: Label your playlist (e.g., "Seasonal", "Training")
4. **Select Categories**: Classify your playlist (e.g., "Marketing", "Internal")
5. Click **Create**

### 3. **Playlist Editing**
Update tags and categories on existing playlists:
1. Go to **Playlists** > Select a playlist > **Edit**
2. Use the tag/category multi-select dropdowns
3. Changes save when you click **Update Playlist**

## Managing Tags and Categories

### Creating Tags
1. Navigate to **Organize** > **Tags** (in top navigation)
2. Click **Create Tag**
3. Enter tag name and choose a color
4. Click **Create**

**Tag Features:**
- Custom colors for visual identification
- Usage statistics (how many videos/playlists use each tag)
- Quick creation by content managers
- Bulk apply to multiple items

### Creating Categories
1. Navigate to **Organize** > **Categories**
2. Click **Create Category**
3. Enter name, description, and optionally:
   - **Parent Category**: Create sub-categories (e.g., "Marketing" > "Social Media")
   - **Color**: Custom color coding
   - **Icon**: Choose from Bootstrap icons
4. Click **Create**

**Category Features:**
- Hierarchical structure (parent/child relationships)
- Icons for visual recognition
- Description field for documentation
- Admin-only management for consistency

## How Tags and Categories Are Displayed

### Video List (Videos Page)
- Tags appear as colored badges below the video title
- Categories appear as colored badges with icons
- Helps quickly identify content type at a glance

### Playlist Cards (Playlists Page)
- Tags and categories displayed as badges on each playlist card
- Color-coded for easy visual scanning
- Shows organization at a glance

### Upload Modal
- Multi-select dropdowns show all available tags/categories
- Background colors match tag/category colors for easy identification
- Categories show full path (e.g., "Marketing > Social Media")

## Use Cases

### Use Tags For:
✅ Temporary classifications ("Holiday 2024", "Black Friday")
✅ Cross-cutting concerns ("Featured", "Urgent", "Review Needed")
✅ Quick filters and searches
✅ User-generated organization
✅ Flexible, evolving classifications

### Use Categories For:
✅ Permanent organizational structure
✅ Departmental organization ("Marketing", "HR", "IT")
✅ Content type classification ("Training", "Promotional", "Safety")
✅ Hierarchical relationships ("Products" > "Hardware" > "Laptops")
✅ Formal taxonomies

## Filtering (Coming Soon)
Future updates will add:
- Filter videos by tags/categories on the Videos page
- Filter playlists by tags/categories
- API endpoints to query by tags/categories
- Device filtering based on content organization

## Permissions

| Action | Required Role |
|--------|---------------|
| View tags/categories | All users |
| Create/edit tags | Content Manager or Admin |
| Delete tags | Content Manager or Admin |
| Create/edit categories | Admin only |
| Delete categories | Admin only |
| Apply tags to videos/playlists | Content Manager or Admin |
| Apply categories to videos/playlists | Content Manager or Admin |

## Best Practices

1. **Start with Categories**: Define your main organizational structure first
2. **Use Consistent Naming**: Follow a naming convention (Title Case recommended)
3. **Limit Tag Count**: Don't create too many tags - merge similar ones
4. **Color Code Thoughtfully**: Use colors consistently (e.g., red for urgent, blue for informational)
5. **Review Regularly**: Clean up unused tags and reorganize categories as needed
6. **Document Categories**: Use description fields to explain category purpose
7. **Train Your Team**: Ensure everyone understands when to use tags vs. categories

## Examples

### Marketing Department Setup
**Categories:**
- Marketing (parent)
  - Social Media (child)
  - Email Campaigns (child)
  - Trade Shows (child)

**Tags:**
- Q1-2025
- Q2-2025
- Featured
- New
- Archived

### Training Content Setup
**Categories:**
- Training (parent)
  - Safety (child)
  - Onboarding (child)
  - Software (child)
  - Compliance (child)

**Tags:**
- Required
- Optional
- Updated-2025
- Annual-Review

## API Integration (Current)
Videos and playlists returned via the device API now include:
- `tags`: Array of tag objects with id, name, and color
- `categories`: Array of category objects with id, name, color, icon, and full_path

This allows devices to:
- Display content organization to users
- Filter content based on tags/categories
- Implement smart playlists
- Show contextual information

---

**Questions?** Check the main README.md or contact your system administrator.
