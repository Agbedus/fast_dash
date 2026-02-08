---
name: Frontend Development
description: Advanced guidelines for frontend development using HTML, Tailwind CSS, JavaScript, and Jinja2 templates in FastAPI.
---

# Frontend Development Skill

This skill provides "insane" level guidelines and best practices for building high-performance, accessible, and modern frontend interfaces.

## 📚 Essential Resources

- **Roadmap.sh Frontend**: [https://roadmap.sh/frontend](https://roadmap.sh/frontend)
- **Tailwind CSS Docs**: [https://tailwindcss.com/docs](https://tailwindcss.com/docs)
- **MDN Web Docs**: [https://developer.mozilla.org/en-US/](https://developer.mozilla.org/en-US/)

## 🚀 Advanced Best Practices

### HTML & Accessibility (A11y)

1.  **Semantic HTML is Non-Negotiable**: Use `<main>`, `<nav>`, `<article>`, `<section>`, `<aside>` correctly. Divs are a last resort.
2.  **ARIA Labels**: Ensure every interactive element has an accessible name (`aria-label` or `aria-labelledby`) if the text content isn't descriptive enough.
3.  **Keyboard Navigation**: Test that all interactive elements are reachable and usable via keyboard (`Tab`, `Enter`, `Space`).
4.  **Lighthouse Audits**: Aim for 100/100 on Lighthouse accessibility scores.

### Tailwind CSS Mastery

1.  **Mobile-First Design**: Always write un-prefixed utilities for mobile first, then add `md:`, `lg:`, `xl:` for larger screens.
2.  **JIT & Optimization**: Ensure the JIT (Just-In-Time) engine is enabled (default in v3+). Use arbitrary values `w-[32rem]` only when design tokens fail.
3.  **Component Abstraction**: Use `@apply` in CSS files _sparingly_. Prefer extracting repeated patterns into Jinja2 components or macros rather than creating CSS classes.
4.  **Dark Mode**: Implement native dark mode support using `dark:` prefix (`dark:bg-slate-900`) and respect system preferences.

### JavaScript & Performance

1.  **Defer by Default**: All generic scripts should have `defer` attributes.
2.  **Async/Await**: Use modern `async`/`await` for all asynchronous operations. Avoid callback hell.
3.  **Fetch Wrapper**: Create a centralized `fetch` wrapper to handle 401/403 errors, headers (CSRF tokens), and JSON parsing automatically.
4.  **Debounce/Throttle**: Implement debouncing for search inputs and throttling for scroll events to prevent performance bottlenecks.

### Jinja2 "Insane" Patterns

1.  **Macro Systems**: Use `{% macro input(name, value='', type='text') %}` for reusable UI elements like form fields, buttons, and cards.
2.  **Inheritance Depth**: Keep inheritance flat (Base -> Layout -> Page). Avoid deep chains.
3.  **Context Processors**: Use FastAPI context processors to inject global variables (like user info, current year) into all templates without passing them from every endpoint.

## ⚡️ Performance Checklist

- [ ] Images are lazy-loaded (`loading="lazy"`).
- [ ] Critical CSS is inline (if possible), non-critical is deferred.
- [ ] Fonts are preloaded/subsetted.
- [ ] JavaScript bundles are minimized (if using a bundler).
