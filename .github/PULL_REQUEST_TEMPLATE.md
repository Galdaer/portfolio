## Pull Request Checklist

### Code Quality & Architecture
- [ ] Functions follow single responsibility principle (see `.github/instructions/tasks/shell-refactoring.instructions.md`)
- [ ] Complex conditional logic is extracted into separate functions
- [ ] Functions are testable in isolation
- [ ] No functions >20 lines with multiple logical sections
- [ ] Detection logic is separate from validation logic

### Healthcare Compliance
- [ ] Medical data handling follows PHI protection patterns
- [ ] No `# type: ignore` used in healthcare modules
- [ ] Medical disclaimers included in healthcare functions
- [ ] Synthetic data used for testing (no real PHI)

### Security & Performance
- [ ] Security-sensitive operations properly validated
- [ ] Performance patterns follow healthcare efficiency guidelines
- [ ] Error messages don't expose sensitive configuration

### Testing & Documentation
- [ ] Unit tests cover individual function responsibilities
- [ ] Healthcare scenarios tested with synthetic data
- [ ] Documentation updated for function refactoring changes

---

*This template incorporates the refactoring patterns established in bootstrap.sh environment validation improvements.*
