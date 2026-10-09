# Button groups, colors and icons

Status: Idea

## Context
With many projects, the Permanent list gets long. Buttons that belong to one project (e.g. `A / renders`, `A / textures`, `A / output`) should be visually grouped.

## Approach
- `FolderEntry` gets optional `group` and `color` fields. Old JSON stays compatible because missing fields mean no group and the default color.
- The Edit dialog gets a Group combo (editable) and a color picker.
- Each section renders collapsible group headers with the buttons under them. Reorder works within a group and between groups.
- Optional: a custom icon or emoji per button.
- Changing a group or color counts as a Permanent change, so it is recorded in the history.
