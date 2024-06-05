# -*- coding: utf-8 -*-
import requests
import asyncio
import traceback

from src.trackers.COMMON import COMMON
from src.console import console


class SN():

    def __init__(self, config):
        self.config = config
        self.tracker = 'SN'
        self.source_flag = 'Swarmazon'
        self.upload_url = 'https://swarmazon.club/api/upload.php'
        self.search_url = 'https://swarmazon.club/api/search.php'     
        self.banned_groups = [""]
        pass

    async def get_type_id(self, type):
        type_id = {
            'BluRay': '3',
            'Web': '1',
            # boxset is 4
            #'NA': '4',
            'DVD': '2'
        }.get(type, '0')
        return type_id

    async def upload(self, meta):
        common = COMMON(config=self.config)
        await common.edit_torrent(meta, self.tracker, self.source_flag)
        #await common.unit3d_edit_desc(meta, self.tracker, self.forum_link)
        await self.edit_desc(meta)
        cat_id = ""
        sub_cat_id = ""
        #cat_id = await self.get_cat_id(meta)
        if meta['category'] == 'MOVIE':
            cat_id = 1
            # sub cat is source so using source to get
            sub_cat_id = await self.get_type_id(meta['source'])
        elif meta['category'] == 'TV':
            cat_id = 2
            if meta['tv_pack']:
                sub_cat_id = 6
            else:
                sub_cat_id = 5
            # todo need to do a check for docs and add as subcat


        if meta['bdinfo'] != None:
            mi_dump = None
            bd_dump = open(f"{meta['base_dir']}/tmp/{meta['uuid']}/BD_SUMMARY_00.txt", 'r', encoding='utf-8').read()
        else:
            mi_dump = open(f"{meta['base_dir']}/tmp/{meta['uuid']}/MEDIAINFO.txt", 'r', encoding='utf-8').read()
            bd_dump = None
        desc = open(f"{meta['base_dir']}/tmp/{meta['uuid']}/[{self.tracker}]DESCRIPTION.txt", 'r').read()

        with open(f"{meta['base_dir']}/tmp/{meta['uuid']}/[{self.tracker}]{meta['clean_name']}.torrent", 'rb') as f:
            tfile = f.read()
            f.close()

        # uploading torrent file.
        files = {
            'torrent': (f"{meta['name']}.torrent", tfile)
        }

        # adding bd_dump to description if it exits and adding empty string to mediainfo
        if bd_dump:
            desc += "\n\n" + bd_dump
            mi_dump = ""

        data = {
            'api_key': self.config['TRACKERS'][self.tracker]['api_key'].strip(),
            'name': meta['name'],
            'category_id': cat_id,
            'type_id': sub_cat_id,
            'media_ref': f"tt{meta['imdb_id']}",
            'description': desc,
            'media_info': mi_dump

        }

        if not meta['debug']:
            success = False
            data = {}
            try:
                response = requests.post(url=self.upload_url, files=files, data=data)
                response.raise_for_status()                
                response_json = response.json()
                success = response_json.get('success', False)
                data = response_json.get('data', {})
            except Exception as e:
                console.print(f"[red]Encountered Error: {e}[/red]\n[bold yellow]May have uploaded, please go check..")
            if success:
                console.print("[bold green]Torrent uploaded successfully!")
            else:
                console.print("[bold red]Torrent upload failed.")

            if 'name' in data and 'The name has already been taken.' in data['name']:
                console.print("[red]Name has already been taken.")
            if 'info_hash' in data and 'The info hash has already been taken.' in data['info_hash']:
                console.print("[red]Info hash has already been taken.")
            return success
        
        else:
            console.print("[cyan]Request Data:")
            console.print(data)



    async def edit_desc(self, meta):
        base = open(f"{meta['base_dir']}/tmp/{meta['uuid']}/DESCRIPTION.txt", 'r').read()
        with open(f"{meta['base_dir']}/tmp/{meta['uuid']}/[{self.tracker}]DESCRIPTION.txt", 'w') as desc:
            desc.write(base)
            images = meta['image_list']
            if len(images) > 0:
                desc.write("[center]")
                for each in range(len(images)):
                    web_url = images[each]['web_url']
                    img_url = images[each]['img_url']
                    desc.write(f"[url={web_url}][img=720]{img_url}[/img][/url]")
                desc.write("[/center]")
            desc.write(f"\n[center][url={self.forum_link}]Simplicity, Socializing and Sharing![/url][/center]")
            desc.close()
        return


    async def search_existing(self, meta):
        dupes = {}
        console.print("[yellow]Searching for existing torrents on site...")

        params = {
            'api_key' : self.config['TRACKERS'][self.tracker]['api_key'].strip()
        }

        # using title if IMDB id does not exist to search
        if meta['imdb_id'] == 0:
            if meta['category'] == 'TV':
                params['filter'] = meta['title'] + f"{meta.get('season', '')}{meta.get('episode', '')}" + " " + meta['resolution']
            else:
                params['filter'] = meta['title']
        else:
            #using IMDB_id to search if it exists.
            if meta['category'] == 'TV':
                params['media_ref'] = f"tt{meta['imdb_id']}"
                params['filter'] = f"{meta.get('season', '')}{meta.get('episode', '')}" + " " + meta['resolution']
            else:
                params['media_ref'] = f"tt{meta['imdb_id']}"
                params['filter'] = meta['resolution']

        try:
            response = requests.get(url=self.search_url, params=params)
            response = response.json()
            for i in response['data']:
                result = i['name']
                try:
                    size = i['size']
                except Exception:
                    size = 0    
                dupes[result] = size
        except:
            console.print('[red]Unable to search for existing torrents on site. Either the site is down or your API key is incorrect')
            await asyncio.sleep(5)

        return dupes
