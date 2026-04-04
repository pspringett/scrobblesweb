same_commit(){
    set -- $(git show-ref --hash --verify "$@")
    [ "$1" = "$2" ]
}
# get the changes if any, but don't merge them yet
git fetch origin
# See if there are any changes
if same_commit mainline origin/mainline
then
   echo "Everything up to date"
   exit 0
fi
# Now merge the remote changes
git pull origin
touch /var/www/pspringett_eu_pythonanywhere_com_wsgi.py