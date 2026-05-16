# UI

The UI will contain the following:

- A toolbar with buttons (icons only, with tooltip):
  - Back (Left arrow)
  - Forward (Right arrow)
  - *Spacing*
  - Search box with placeholder "Filter images"
  - Filter icon. On press, show context menu. This context menu is the "Filter menu" and will also be duplicated elsewhere:
      - Name
      - Date Created
      - Date Modified
      - (Separator)
      - (checkbox) Descending
      - (checkbox) Natural Sort

- 2 resizable columns:
  - to the left, defaulting to 80% of width is the "ImageView". Create a new class for this. For now, just make it display dark gray with "Select an image..."
  - to the right contains 2 resizable rows (default 50% each):
    - a tab view with the tabs. For now they contain nothing:
      - Directory
      - Tags
    - A QListView "ImageDetailList". This is a ListMode, resize mode=Adjust layout mode=Batched, movement=Static, uniform item size view. This will store the model "ImageDetailModel". The ImageDetailModel will contain a thumbnail to the left and the file name to the right.
