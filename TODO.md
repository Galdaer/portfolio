### Justin

---

Wireguard, only services work? Switch bootstrap to be VPN only always and get rid of prompts for that as well as mergerfs or other unneeded prompts

Vaultwarden?

Is phase 0 .gitignore right or do we need to combine with the current one (keeping in mind it excludes everything by default at the top)? Planning and decisions 

Is this not just copying scripts into the directory they're already in?
cp -r ../intelluxe/scripts/universal-service-runner.sh ./scripts/
cp -r ../intelluxe/scripts/clinic-bootstrap.sh ./scripts/

Can we make ci not run for just doc updates?

What users can access /home/intelluxe? User group that is set by bootstrap? Or is the bootstrap only setting it for a specific user right now?

Do we need to make sure that we include proper stuff for the fact that things like AI engineering hub are MIT licensed even though we're closed source?

Should the mini PC username be something other than Intelluxe since we put docker-stack in /home/intelluxe right?

Will we actually use traefik or is there a better standard for IT that we are/should be planning?

Should we be testing everything in a VM so it doesn't break the mini PC? If this repo is the only thing on it can it really break much? Or is this why we should run things in venv first? Or is it why we should use my CI runner first? Both? Either?

Should we copy AI engineering hub repo somewhere so copilot can better reference its code?

Do we ever really need to do visual processing, can't all that be done in the cloud without using identifying information, and it's usually not time sensitive enough to need to fallback to local models during hiccups?

Is Scispacy gone from or plans, or is it basically part of undocumented phase 4 or 5 mentioned at bottom of phase 2? I know we have the config already but did we forget the implementation?

https://docs.github.com/en/enterprise-cloud@latest/admin/managing-your-enterprise-account/about-enterprise-accounts

https://www.notebookcheck.net/Hidden-flaw-in-Linux-Ubuntu-and-Fedora-laptops-allows-full-system-compromise.1052011.0.html

https://simonwillison.net/2025/Jul/6/supabase-mcp-lethal-trifecta/

https://trufflesecurity.com/blog/guest-post-how-i-scanned-all-of-github-s-oops-commits-for-leaked-secrets

https://techxplore.com/news/2025-07-speechssm-possibilities-hour-ai-voice.html

https://cybersecuritynews-com.cdn.ampproject.org/v/s/cybersecuritynews.com/hackers-actively-attacking-linux-ssh-servers/amp/?amp_gsa=1&amp_js_v=a9&usqp=mq331AQGsAEggAID#amp_tf=From%20%251%24s&aoh=17518253161408&csi=0&referrer=https%3A%2F%2Fwww.google.com&ampshare=https%3A%2F%2Fcybersecuritynews.com%2Fhackers-actively-attacking-linux-ssh-servers%2F
https://dev.to/sroy8091/my-own-hld-designer-darwin-57np/comments

https://dev.to/anthonymax/9-open-source-gems-to-become-the-ultimate-developer-2pnb