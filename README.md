## How to add your instance to the list?

Create a new issue here: https://github.com/searxng/searx-instances/issues/new/choose

## For SearXNG instance operators

* [Create an issue](https://github.com/searxng/searx-instances/issues/new/choose) to add / remove / edit a SearXNG instance on https://searx.space/
* If you add a new instance, allow the IPs of ```check.searx.space``` to access your instance. It will checks your instance periodically ([source code](https://github.com/searxng/searx-space)). The results are displayed on https://searx.space/
* Wait for a reviewer to actually change [searxstats/instances.yml](https://github.com/searxng/searx-instances/blob/master/searxinstances/instances.yml)

## For reviewers

### Add a new instance to the public list

* create a virtualenv, and then install `searxinstances`:

```python -m pip install .[update]```

* then `searxinstances` can help to edit instances.yml :
```
usage: searxinstances [-h] [--github-issues [GITHUB_ISSUE_LIST [GITHUB_ISSUE_LIST ...]]] [--add [ADD_INSTANCES [ADD_INSTANCES ...]]] [--delete [DELETE_INSTANCES [DELETE_INSTANCES ...]]] [--edit [EDIT_INSTANCES [EDIT_INSTANCES ...]]]

Update the instance list according to the github issues.

optional arguments:
  -h, --help            show this help message and exit
  --github-issues [GITHUB_ISSUE_LIST [GITHUB_ISSUE_LIST ...]]
                        Github issue number to process, by default all
  --add [ADD_INSTANCES [ADD_INSTANCES ...]]
                        Add instance(s)
  --delete [DELETE_INSTANCES [DELETE_INSTANCES ...]]
                        Delete instance(s)
  --edit [EDIT_INSTANCES [EDIT_INSTANCES ...]]
                        Edit instance(s)
```

Or if you don't want to use virtualenv:

1. `pip install .[update]`
2. `python -m searxinstances.update`

The tool :
* is only an helper. instances.yml can be edited directly.
* shows the default editor to only edit one instance at a time.
* once the user quits the editor, the script checks everything is okay, if not it goes back to the editor with the error added at the end of the buffer.
* if everything is okay, the script modifies the instances.yml file.
* then it creates a commit.
* The ```--github-issues``` options reads the [github issues](https://github.com/searxng/searx-instances/issues).

---

An example what is shown in the default editor:
```
https://nibblehole.com: {}

# Add https://nibblehole.com
#
# Close https://github.com/searxng/searx-instances/issues/2
# From @dalf

#> The above text is the commit message
#> Delete the whole buffer to cancel the request

#> -- MESSAGE -----------------------
#> See https://github.com/searxng/ ...
```

Here is it possible to modify the yaml, the commit message and validate or delete the whole buffer to cancel.

### 2-week hold for new instances

All new instance requests must wait 2 weeks before being added. Apply the `wait-2-weeks` label when an instance has been deemed ready for addition. After 2 weeks, verify the instance has been kept up to date before adding it to the list.

### Adding a previously submitted instance

This applies only to instances that were previously added to the list and later removed (e.g. due to errors or bad uptime):

1. Add the domain to the uptime tracker custom list to monitor stability: https://github.com/searxng/searx-instances-uptime/blob/master/.upptimerc-custom.yml
2. Follow the general 2-week hold.
3. After this period, verify the instance has been kept up to date and meets the uptime requirement of >95% (16.8h). If it does, it can be added back and removed from the custom list. If not, do not add the instance.
