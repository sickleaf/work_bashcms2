#!/bin/bash -euvx
source "$(dirname $0)/conf"
source "$(dirname $0)/local/localconf"
exec 2>> "$logdir/$(date +%Y%m%d).$(basename $0)"
#[ -n "${CONTENT_LENGTH}" ] && dd bs=${CONTENT_LENGTH} > /dev/null
tmp=/tmp/$$  #追加

echo -e 'Content-type: text/html\n'

functionScript=${myScript}/common/usefulFunction.sh
filterScript=${myScript}/common/getSpreadSheet.sh

### read function 
. ${functionScript}
. ${filterScript}

cd "$contentsdir"
# make /var/www/.ssh permission as www-data:www-data, and register public key into $contentsdir repository
#git fetch origin master
#git diff --name-status HEAD origin/master  |
#grep -Eo '(posts|pages)/[^/]+'             |
#sort -u                                    > $tmp-git-change

#git pull
#
#[ -f "$datadir/INIT" ] &&
#find posts pages -type d       |
#grep -Eo '(posts|pages)/[^/]+' > $tmp-git-change
#
#rm -f "$datadir/INIT"

### repository status ###
find "$contentsdir" -name "main.md"     |
xargs -I@ bash -c "getLatestGitDate @"  |
sort -r |
sed "s;/var/www/bashcms2_sample/;;g; s;/main.md;;g " > /tmp/repo_status


### get datafolder info ###
find /var/www/bashcms2_sample_data/ -name "modified_time"       |
sed -r "s/(.*)/cat \1,\1/g"     |
teip -d, -f1 -- sh -    |
sort -r |
sed "s;/var/www/bashcms2_sample_data/;;g; s;/modified_time;;g" > /tmp/modify

#diff /tmp/repo_status /tmp/modify | sed -n "/^</p" | cut -d, -f2

diff /tmp/repo_status /tmp/modify |
sed -n "/^</p" |
cut -d, -f2 > $tmp-git-change


### CREATE/DELETE ARTICLE DIRECTORY ###
cat $tmp-git-change |
while read d ; do
    [ -f "$contentsdir/$d/main.md" ] || rm -Rf "$datadir/$d"
    [ -f "$contentsdir/$d/main.md" ] || continue

    mkdir -p "$datadir/$d"           &&
    ### ADD TIME FILES ###
    git log -p "$contentsdir/$d/main.md" |
    grep '^Date:'                        |
    awk '{print $2,$3,$4,$5,$6}'         |
    date -f - "+%Y-%m-%d %H:%M:%S"       |
    awk -v cf="$datadir/$d/created_time" \
        -v mf="$datadir/$d/modified_time" \
        'NR==1{print > mf}END{print > cf}'

    ### MAKE SOME SNIPS ###
    grep -m 1 '^# ' "$contentsdir/$d/main.md"           |
    sed 's/^#  *//'                                     |
    awk '{if(/^$/){print "NO TITLE"}else{print}}
         END{if(NR==0){print "NO TITLE"}}'              |
    tee "$datadir/$d/title"                             |
    awk -v d="$d" '{gsub(/s\//,"=",d);
        print "<a href=\"/?" d "\">" $0 "</a>"}' > "$datadir/$d/link"

    ymd=$(sed 's/ .*//' < "$datadir/$d/created_time")
    sed "s;</a>; ($ymd)&;" "$datadir/$d/link" > "$datadir/$d/link_date"

    touch "$datadir/$d/nav"
done

### MAKE POST/PAGE LIST ###
touch "$datadir/post_list"
cp "$datadir/post_list" $tmp-old-post-list

# LIST POSTS DATA
cd "$datadir"
find posts pages -type f     |
grep created_time            |
xargs grep -H .              |
sed 's;/created_time:; ;'    |
awk '{print $2,$3,$1}'       |
sort -k1,2                   |
tee $tmp-list                |
awk '$3~/^posts/'            > $tmp-post_list
mv $tmp-post_list "$datadir/post_list"

# LIST PAGES DATA
awk '$3~/^pages/' $tmp-list  > $tmp-page_list
mv $tmp-page_list "$datadir/page_list"

# MAKE POST LIST WITH DELETED POSTS
sort -m $tmp-old-post-list "$datadir/post_list" |
uniq > $tmp-new-old-list

#cat $tmp-git-change > /tmp/changed    # デバッグ用

# MAKE LIST OF POSTS WHOSE NAV MUST BE CHANGED
cat $tmp-git-change                             |
xargs -I@ -n 1 grep -C1 "@$" $tmp-new-old-list  |
sort -u                                         |
while read ymd hms d ; do
        [ -f "$contentsdir/$d/main.md" ] || continue
        grep -C1 "$d$" "$datadir/post_list"                             |
        awk '{print $3}'                                                |
        sed -n -e '1p' -e '$p'                                          |
        xargs -I@ cat "$datadir/@/link"                                 |
        awk 'NR<=2{print}END{for(i=NR;i<2;i++){print "LOST TITLE"}}'    |
        sed -e '1s/^/前の記事:/' -e '2s/^/次の記事:/'                           |
        tr '\n' ' '                                     > "$datadir/$d/nav"
done

### MAKE KEYWORD LIST ###
cd "$contentsdir"
cat $tmp-list                    |
awk '{print $3 "/main.md"}'      |
xargs grep -H -m 1 '^Keywords:'  |
sed 's;/main.md:Keywords:; ;'    |
sed 's/ *, */,/g'                |
sed 's/  */ /g'                  |
awk '{gsub(/^/,",",$2);print}'   |
sed 's/$/,/'                     > $tmp-keyword_list
mv $tmp-keyword_list "$datadir/keyword_list"

### MAKE SEARCH FILE ###
cd "$contentsdir"
cat $tmp-list                    |
awk '{print $3 "/main.md"}'      |
xargs grep -H ^                  |
sed 's;/main.md:; ;'             |
awk 'a!=$1{c=0;a=$1}c>=2{print}$2~/^---$/{c++}' |
awk '$2~/^\*$|^#*$/{$2=""}{print}'              |
awk 'NF>1'                      > $tmp-all
mv $tmp-all "$datadir/all_markdown"

rm -f $tmp-*
