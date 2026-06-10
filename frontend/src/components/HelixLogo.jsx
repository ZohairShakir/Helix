/**
 * Shared Helix brand logo mark.
 */

import { cn } from '../lib/utils'

export default function HelixLogo({ className, size = 'md', alt = 'Helix' }) {
  const sizes = {
    sm: 'w-8 h-8',
    md: 'w-10 h-10',
    lg: 'w-14 h-14',
    xl: 'w-20 h-20',
  }

  return (
    <img
      src="/helix-logo.png"
      alt={alt}
      className={cn('rounded-lg object-cover', sizes[size] ?? sizes.md, className)}
    />
  )
}
