from google.appengine.ext import vendor
vendor.add('lib')
# This supposedly helps fix bug with importing oauth2client
# I had to dump all oauth2client files into the project directory
# and install manually to get the client to work with Google app Engine
# citation: https://stackoverflow.com/questions/44011776/how-to-prevent-importerror-no-module-named-oauth2client-client-on-google-app