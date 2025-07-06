
## n8n Research & Learning Checklist

### 1. **Core Concepts**
- What is n8n? ([Official Docs](https://docs.n8n.io/))
- How n8n workflows work: nodes, triggers, data flow
- Understanding credentials and environment variables in n8n

### 2. **Installation and Setup**
- Running n8n locally (Docker, desktop, or server)
- Accessing the n8n web UI
- Setting up persistent storage for workflows (important for production use)
- Backing up and exporting/importing workflows

### 3. **Building Workflows**
- Creating a new workflow
- Using HTTP Request nodes to call your backend scripts/APIs
- Passing data between nodes (variable handling, references)
- Using built-in nodes (Set, Merge, IF, Switch, Wait, SplitInBatches, etc.)
- Error handling and notifications in workflows

### 4. **Authentication and Security**
- Setting up credentials for secure API calls (API keys, headers, Basic Auth, etc.)
- Setting up environment variables for secrets (never hardcode secrets in nodes!)
- Using n8n behind VPN or with access control

### 5. **Testing and Debugging**
- Running and debugging workflows step by step
- Inspecting node outputs and error logs
- Using mock/test data for initial development

### 6. **Production Practices**
- Scheduling workflows (cron, interval, webhook triggers)
- Notification and alerting (e.g., email or chat on failures)
- Monitoring workflow runs for errors or performance issues

### 7. **Integration with Other Tools**
- Connecting with email, Slack/Teams, file storage, SFTP, etc. (as needed for your workflows)
- Using Webhook nodes to receive data (e.g., from Windows audio upload)
- Chaining multiple backend endpoints in a single workflow

### 8. **Documentation and Maintenance**
- Best practices for documenting workflows (naming, descriptions, comments)
- Exporting/importing workflows for sharing or backup
- Version control for workflow definitions (manual, via export files)

---

## Good Resources for n8n

- [n8n Documentation](https://docs.n8n.io/)
- [n8n YouTube Channel](https://www.youtube.com/c/n8n_io)
- [n8n Community Forum](https://community.n8n.io/)
- Example workflows: [n8n.io/workflows](https://n8n.io/workflows)
- [How to use HTTP Request node](https://docs.n8n.io/nodes/n8n-nodes-base.httpRequest/)
- [Environment Variables guide](https://docs.n8n.io/hosting/environment-variables/)

---

## Suggested First Projects

1. **"Hello World"**: Make a simple workflow that calls an endpoint you wrote and logs the output.
2. **Chain Two Endpoints**: Get data from one script, pass it to another, and process the result.
3. **Error Handling**: Build a workflow that intentionally fails and see how to catch/report the error.
4. **Data Passing**: Practice transforming and mapping data from one node to the next.
5. **Webhook Trigger**: Set up a workflow that starts when a file is uploaded or an event occurs.

---

## Tips for Collaboration

- As soon as you have a new endpoint or script, provide your dad with its docs and sample curl requests.
- Ask him to build or update the matching n8n workflow and report any issues with data, errors, or chaining.
- Review and test workflows together periodically.
