

same_commit(){
    set -- $(git show-ref --hash head/main remotes/origin/main)
    [ "$1" = "$2" ]
}
# get the changes if any, but don't merge them yet
git fetch origin

# See if there are any changes
if same_commit
then
   echo "Everything up to date"
   exit 0
fi
# Now merge the remote changes and touch the wsgi file to trigger a reload of the app.
git pull origin
touch /var/www/pspringett_eu_pythonanywhere_com_wsgi.py