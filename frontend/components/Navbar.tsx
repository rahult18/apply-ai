"use client"

import Link from "next/link"
import { usePathname } from "next/navigation"
import { useAuth } from "@/contexts/AuthContext"
import { Button } from "@/components/ui/button"
import {
  NavigationMenu,
  NavigationMenuItem,
  NavigationMenuLink,
  NavigationMenuList,
  navigationMenuTriggerStyle,
} from "@/components/ui/navigation-menu"
import { cn } from "@/lib/utils"

export function Navbar() {
  const pathname = usePathname()
  const { user, logout } = useAuth()

  return (
    <nav className="bg-white border-b sticky top-0 z-50">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex justify-between h-16 items-center">
          <h1 className="text-xl font-semibold">ApplyAI</h1>
          
          <div className="flex items-center gap-4">
            <NavigationMenu>
              <NavigationMenuList>
                <NavigationMenuItem>
                  <Link href="/home" legacyBehavior passHref>
                    <NavigationMenuLink
                      className={cn(
                        navigationMenuTriggerStyle(),
                        "cursor-pointer",
                        pathname === "/home" && "bg-accent"
                      )}
                    >
                      Home
                    </NavigationMenuLink>
                  </Link>
                </NavigationMenuItem>
                <NavigationMenuItem>
                  <Link href="/home/add" legacyBehavior passHref>
                    <NavigationMenuLink
                      className={cn(
                        navigationMenuTriggerStyle(),
                        "cursor-pointer",
                        pathname === "/home/add" && "bg-accent"
                      )}
                    >
                      Add to tracker
                    </NavigationMenuLink>
                  </Link>
                </NavigationMenuItem>
                <NavigationMenuItem>
                  <Link href="/home/profile" legacyBehavior passHref>
                    <NavigationMenuLink
                      className={cn(
                        navigationMenuTriggerStyle(),
                        "cursor-pointer",
                        pathname === "/home/profile" && "bg-accent"
                      )}
                    >
                      Profile
                    </NavigationMenuLink>
                  </Link>
                </NavigationMenuItem>
              </NavigationMenuList>
            </NavigationMenu>
            
            {user && (
              <div className="flex items-center gap-4">
                <span className="text-sm text-muted-foreground">{user.email}</span>
                <Button variant="outline" onClick={logout}>
                  Logout
                </Button>
              </div>
            )}
          </div>
        </div>
      </div>
    </nav>
  )
}

