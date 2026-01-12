# Claude Code + Kiro System Integration

This is a generic template for adding Amazon's Kiro system to your project's CLAUDE.md file. Copy the section below into your own CLAUDE.md file and customize it for your project.

## Template Section to Add to Your CLAUDE.md

```markdown
## Kiro System - Adaptation of Amazon's Spec-Driven Development

This project uses an adaptation of Amazon's **Kiro System** for structured feature development. The original Kiro system has been adapted to work with Claude Code through templates and workflow guidance.

### Kiro Workflow (Amazon's 3-Phase Approach)
1. **Requirements** (`requirements.md`) - What needs to be built
2. **Design** (`design.md`) - How it will be built  
3. **Tasks** (`tasks.md`) - Step-by-step implementation plan

### Directory Structure
- `.kiro/specs/{feature-name}/` - Individual feature specifications
- `.kiro/kiro-system-templates/` - Templates and documentation
  - `requirements-template.md` - Template for requirements
  - `design-template.md` - Template for technical design
  - `tasks-template.md` - Template for implementation tasks
  - `how-kiro-works.md` - Detailed Kiro documentation

### How Claude Code Should Work with Kiro

#### When Asked to Create New Features:
1. **Check for existing specs first**: Look in `.kiro/specs/` for any existing feature documentation
2. **Use templates**: Copy templates from `.kiro/kiro-system-templates/` when creating new specs
3. **Follow the 3-phase process**: Requirements → Design → Tasks → Implementation
4. **Require approval**: Each phase needs explicit user approval before proceeding

#### Template Usage:
- **Requirements**: Use `requirements-template.md` to create user stories and EARS acceptance criteria
- **Design**: Use `design-template.md` for technical architecture and component design
- **Tasks**: Use `tasks-template.md` to break down implementation into numbered, actionable tasks

#### During Implementation:
- **Reference requirements**: Always link tasks back to specific requirements
- **Work incrementally**: Implement tasks one at a time, not all at once
- **Validate against specs**: Ensure implementations match the design and requirements
- **Update documentation**: Keep specs updated if changes are needed

#### Key Behaviors:
- **Always suggest using Kiro** when user wants to build new features
- **Guide through templates** if user is unfamiliar with the process
- **Enforce the approval process** - don't skip phases
- **Maintain traceability** from requirements to code
```

## Setup Instructions

### 1. Create Directory Structure
```bash
mkdir -p .kiro/specs
mkdir -p .kiro/kiro-system-templates
```

### 2. Copy Templates
Copy these template files to your `.kiro/kiro-system-templates/` directory:
- `requirements-template.md`
- `design-template.md`
- `tasks-template.md`
- `how-kiro-works.md`

### 3. Add to Your CLAUDE.md
Add the template section above to your project's CLAUDE.md file, typically after your project overview but before development notes.

### 4. Customize for Your Project
- Replace `{feature-name}` with your actual feature naming convention
- Adjust the template paths if you use a different directory structure
- Add any project-specific Kiro adaptations

## What This Gives You

### For Your Development Process:
- **Structured feature development** following Amazon's proven methodology
- **Clear documentation** for every feature before coding begins
- **Requirement traceability** from user stories to final code
- **Reduced rework** through thorough upfront planning

### For Claude Code:
- **Context-aware assistance** that understands your project structure
- **Systematic implementation** following the 3-phase process
- **Quality assurance** through requirement validation
- **Consistent patterns** across all features

### For Your Team:
- **Standardized approach** to feature development
- **Clear specifications** for all features
- **Better estimates** through detailed task breakdown
- **Improved collaboration** with shared documentation

## Example Usage

1. **User**: "I want to add a new user authentication feature"
2. **Claude**: "Let's use the Kiro system. First, I'll create requirements.md using the template..."
3. **Process**: Requirements → Design → Tasks → Implementation
4. **Result**: Well-documented, traceable feature implementation

## Tips for Success

- **Always get approval** at each phase before moving forward
- **Keep templates updated** as your project evolves
- **Reference requirements** in every task and implementation
- **Use consistent naming** for your feature specs
- **Review and iterate** on your templates based on what works

---

*This is an adaptation of Amazon's Kiro system for use with Claude Code. The original methodology belongs to Amazon.*