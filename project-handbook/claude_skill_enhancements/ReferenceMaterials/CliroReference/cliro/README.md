# Kiro System Adaptation for Claude Code

This is an adaptation of Amazon's Kiro system to work with Claude Code. The original Kiro system is Amazon's internal spec-driven development methodology - I've just added templates and configuration to make it work nicely with Claude Code.

## What is Kiro?

Kiro is Amazon's approach to breaking down features into three phases:
1. **Requirements** - What needs to be built
2. **Design** - How it will be built  
3. **Tasks** - Step-by-step implementation plan

Instead of jumping straight into code, you plan everything out first. Each phase needs approval before moving to the next.

## How I've Adapted It

I've created templates and configured Claude Code to understand the Kiro workflow:

### Directory Structure
```
.kiro/
├── specs/                          # Feature specifications
│   └── {feature-name}/            # Individual feature folder
│       ├── requirements.md        # What needs to be built
│       ├── design.md             # How it will be built
│       └── tasks.md              # Step-by-step implementation
└── kiro-system-templates/         # Templates and docs
    ├── requirements-template.md   # Requirements template
    ├── design-template.md        # Design template
    ├── tasks-template.md         # Tasks template
    ├── claude_agnostic.md        # Generic Claude Code integration
    └── how-kiro-works.md         # Detailed Kiro documentation
```

### Claude Code Integration

I've updated the project's `CLAUDE.md` file so Claude Code knows about:
- The three-phase Kiro workflow
- How to use the templates
- Where to find existing specs
- How to create new feature specs

### Reusable for Any Project

The `claude_agnostic.md` file contains a generic template that any developer can:
- Copy into their own project's CLAUDE.md file
- Use to set up the Kiro system in any codebase
- Share with other developers for consistent AI-assisted development

## The Workflow

1. **Requirements Phase**: Use the requirements template to document user stories and acceptance criteria
2. **Design Phase**: Create technical design with architecture and components
3. **Tasks Phase**: Break down into actionable coding tasks
4. **Implementation**: Claude Code executes tasks incrementally

Each phase requires approval before moving to the next.

## Templates

### Requirements Template
- User stories format
- EARS acceptance criteria (Easy Approach to Requirements Syntax)
- Technical architecture overview
- Success criteria

### Design Template
- System architecture
- Component interfaces
- Data models
- Error handling
- Testing strategy

### Tasks Template
- Numbered implementation tasks
- Clear deliverables
- Requirements traceability
- Progress tracking

## Using It

### For This Project:
1. Create a new feature folder in `.kiro/specs/`
2. Copy the relevant templates
3. Fill out requirements and get approval
4. Create design and get approval
5. Create tasks and get approval
6. Let Claude Code implement the tasks

### For Other Projects:
1. Copy the `claude_agnostic.md` content into your project's CLAUDE.md
2. Set up the `.kiro/` directory structure
3. Copy the templates to your project
4. Start using structured development with Claude Code

### Sharing with Others:
The `claude_agnostic.md` file makes it easy to share this system:
- Send the file to other developers
- Include it in project documentation
- Use it as a starting point for team adoption

## Why This Works

Claude Code works better with structured context. The Kiro approach gives it:
- Clear requirements to validate against
- Detailed design to follow
- Specific tasks to implement
- Traceability from requirements to code

It's basically taking Amazon's proven approach and making it work with AI coding assistants.

---

*Just my adaptation of Amazon's Kiro system to work better with Claude Code. Nothing revolutionary, just practical.*
