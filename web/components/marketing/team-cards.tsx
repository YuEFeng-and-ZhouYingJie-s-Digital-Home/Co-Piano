import { Card, CardContent } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Avatar, AvatarFallback } from '@/components/ui/avatar';
import type { TeamMember } from '@/lib/about-data';

interface TeamCardsProps {
  members: readonly TeamMember[];
}

export function TeamCards({ members }: TeamCardsProps) {
  return (
    <div className="grid gap-6 md:grid-cols-3">
      {members.map((member) => (
        <Card key={member.name} className="text-center">
          <CardContent className="pt-6">
            <Avatar className="mx-auto h-20 w-20">
              <AvatarFallback className="bg-piano-500/10 text-piano-700 dark:text-piano-300 text-2xl font-bold">
                {member.initials}
              </AvatarFallback>
            </Avatar>
            <h3 className="mt-4 text-lg font-semibold">{member.name}</h3>
            <p className="text-sm text-piano-500 font-medium">{member.role}</p>
            <p className="mt-3 text-sm text-muted-foreground leading-relaxed">
              {member.bio}
            </p>
            <div className="mt-4 flex flex-wrap justify-center gap-1.5">
              {member.tags.map((tag) => (
                <Badge key={tag} variant="secondary" className="text-xs">
                  {tag}
                </Badge>
              ))}
            </div>
          </CardContent>
        </Card>
      ))}
    </div>
  );
}
