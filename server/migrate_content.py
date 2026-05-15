#!/usr/bin/env python3
"""One-time migration: convert old nested root.json + flat pages/ to new folder-per-page layout."""

import json
import os
import shutil

CONTENT_DIR = os.path.join(os.path.dirname(__file__), 'content')
PAGES_DIR = os.path.join(CONTENT_DIR, 'pages')


def slug(title):
    return title.lower().replace(' ', '-')


def migrate():
    old_root_path = os.path.join(CONTENT_DIR, 'root.json')
    with open(old_root_path, 'r') as f:
        old_data = json.load(f)

    if 'pages' in old_data:
        print('Already in new format — nothing to do.')
        return

    root = old_data['root']

    # Back up old layout
    backup_dir = os.path.join(CONTENT_DIR, '_pages_backup')
    if not os.path.exists(backup_dir):
        shutil.copytree(PAGES_DIR, backup_dir)
        print(f'Backed up pages/ to _pages_backup/')

    shutil.copy2(old_root_path, old_root_path + '.bak')
    print(f'Backed up root.json to root.json.bak')

    # Move special files to content root
    for special in ['root-header.seq', 'goodbye.seq', 'help.seq']:
        src = os.path.join(PAGES_DIR, special)
        if os.path.exists(src):
            dst_name = 'header.seq' if special == 'root-header.seq' else special
            dst = os.path.join(CONTENT_DIR, dst_name)
            shutil.copy2(src, dst)
            print(f'Copied {special} -> {dst_name}')

    # Process the tree
    new_root = convert_directory(root, CONTENT_DIR)

    # Write new root.json
    with open(old_root_path, 'w') as f:
        json.dump(new_root, f, indent=2)
    print(f'Wrote new root.json')

    # Write global adverts.json
    adverts_path = os.path.join(CONTENT_DIR, 'adverts.json')
    adverts_data = {
        'adverts': [
            'WELCOME TO COMPUNET REBORN!\nTYPE HELP FOR COMMANDS'
        ]
    }
    with open(adverts_path, 'w') as f:
        json.dump(adverts_data, f, indent=2)
    print(f'Wrote adverts.json')

    print('\nMigration complete.')


def convert_directory(dir_node, base_dir):
    """Convert a directory node (with children) into the new flat format."""
    data = {}

    # Header for root
    if dir_node.get('header'):
        data['header'] = 'header.seq' if dir_node['header'] == 'root-header.seq' else dir_node['header']

    data['pages'] = []

    # Track slugs at this level to handle collisions
    used_slugs = {}

    for child in dir_node.get('children', []):
        page_slug = slug(child['title'])

        # Handle slug collisions at the same level
        if page_slug in used_slugs:
            page_slug = f"{page_slug}-{child['page_num']}"
        used_slugs[page_slug] = True

        # Create page folder
        page_dir = os.path.join(base_dir, page_slug)
        os.makedirs(page_dir, exist_ok=True)

        # Copy frame files into page folder
        frame_files = []
        for i, old_frame in enumerate(child.get('frames', [])):
            new_frame = f'frame-{i+1}.seq'
            src = os.path.join(PAGES_DIR, old_frame)
            dst = os.path.join(page_dir, new_frame)
            if os.path.exists(src):
                shutil.copy2(src, dst)
            else:
                print(f'  WARNING: frame not found: {old_frame}')
            frame_files.append(new_frame)

        # Build page entry
        page_entry = {
            'page_num': child['page_num'],
            'title': child['title'],
            'type': child.get('type', 'T'),
            'author': child.get('author', 'SYSTEM'),
            'price': child.get('price', 0),
            'life': child.get('life', 0),
        }

        if child.get('keyword'):
            page_entry['keyword'] = child['keyword']

        if frame_files:
            page_entry['frames'] = frame_files

        # If page has children, create sub-directory
        if child.get('children'):
            sub_dir_rel = f'{page_slug}/directory.json'
            page_entry['directory'] = sub_dir_rel

            # Recursively convert children
            sub_data = convert_directory(child, page_dir)
            sub_json_path = os.path.join(page_dir, 'directory.json')
            with open(sub_json_path, 'w') as f:
                json.dump(sub_data, f, indent=2)
            print(f'  Wrote {sub_dir_rel}')

        data['pages'].append(page_entry)
        print(f'  Migrated page {child["page_num"]} "{child["title"]}" -> {page_slug}/')

    return data


if __name__ == '__main__':
    migrate()
