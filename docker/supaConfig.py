from supabase import create_client

f = open("/run/secrets/supa_key")
g = open("/run/secrets/supa_url")

supa_key = f.read()
supa_url = g.read()

f.close()
g.close()

supa = create_client(supabase_key=supa_key, supabase_url=supa_url)

