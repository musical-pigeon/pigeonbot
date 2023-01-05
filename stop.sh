ps -ux | grep danbooru | grep -v grep | tr -s ' ' | cut -d' ' -f2 | xargs kill
