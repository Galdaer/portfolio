# GitHub Copilot Firewall Configuration for Intelluxe AI

This directory contains firewall configuration for GitHub Copilot to access necessary domains for Intelluxe AI Healthcare System development.

## Quick Setup

### Method 1: Repository Settings (Recommended)
1. Go to your repository **Settings** → **Copilot**
2. Navigate to **Firewall Configuration**
3. Upload or paste the contents of [`copilot-firewall-allowlist.txt`](./copilot-firewall-allowlist.txt)
4. Save the configuration

### Method 2: GitHub CLI
```bash
# Copy the allowlist content and configure via GitHub CLI
gh api repos/:owner/:repo/copilot/firewall --method PUT \
  --field allowlist=@.github/copilot-firewall-allowlist.txt
```

### Method 3: Run Setup Workflow
1. Go to **Actions** → **Copilot Setup Steps for Intelluxe AI Healthcare System**
2. Click **Run workflow**
3. Follow the manual configuration instructions displayed

## What This Configures

### Critical Healthcare AI Infrastructure Access
- **Ubuntu Repositories**: Package installation for development tools
- **Python Package Index**: Healthcare AI dependencies and libraries
- **Docker Infrastructure**: Healthcare container images and orchestration
- **GitHub**: Source control, releases, and CI/CD
- **Node.js/NPM**: n8n workflow automation tools

### Healthcare-Specific Services
- **Ollama**: Local LLM inference infrastructure
- **PostgreSQL**: Healthcare data management
- **Redis**: Session management and caching
- **Medical Research APIs**: PubMed, ClinicalTrials.gov, FDA API (read-only)

### Development Tools
- **VS Code**: Extensions and marketplace
- **Git**: Version control
- **Security Tools**: CVE databases, NIST vulnerability data

## Security & Compliance Notes

### Privacy-First Design
- **No patient data**: All allowlisted domains are for development infrastructure only
- **Read-only APIs**: Medical research APIs provide only public research data
- **Local processing**: Core AI processing uses on-premise infrastructure

### HIPAA Compliance
- All patient data processing remains **on-premise**
- External access is **limited to development tools and public APIs**
- No PHI/PII is transmitted to external services

## Troubleshooting

### Common Issues
1. **Tests failing with DNS resolution errors**
   - Ensure firewall allowlist is properly configured
   - Check that Ubuntu repositories (`archive.ubuntu.com`, `azure.archive.ubuntu.com`) are accessible

2. **Python package installation failures**
   - Verify `pypi.org` and `files.pythonhosted.org` are allowlisted
   - Check network connectivity to Python Package Index

3. **Docker image pulls failing**
   - Ensure Docker Hub domains (`registry-1.docker.io`, `index.docker.io`) are accessible
   - Verify Docker infrastructure is properly configured

### Manual Testing
```bash
# Test Ubuntu repository access
curl -f --connect-timeout 10 https://archive.ubuntu.com/

# Test Python Package Index
curl -f --connect-timeout 10 https://pypi.org/simple/

# Test Docker Hub
curl -f --connect-timeout 10 https://registry-1.docker.io/v2/

# Test GitHub API
curl -f --connect-timeout 10 https://api.github.com/
```

## Files in This Directory

- **`copilot-firewall-allowlist.txt`**: Main firewall allowlist configuration
- **`copilot-setup-steps.yml`**: Automated setup workflow
- **`copilot-instructions.md`**: Development guidelines and coding standards
- **`README.md`**: This documentation file

## Support

For issues with firewall configuration:
1. Check GitHub's [Copilot firewall documentation](https://docs.github.com/en/copilot/managing-copilot/configuring-github-copilot-settings)
2. Verify domain formats match GitHub's requirements
3. Test connectivity manually using the troubleshooting commands above

For Intelluxe AI specific issues:
- Review the main repository documentation
- Check the troubleshooting guide in `/docs/TROUBLESHOOTING.md`
- Ensure all healthcare AI dependencies are properly configured
