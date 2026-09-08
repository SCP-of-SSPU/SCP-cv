using System.Text.Json;
using Microsoft.AspNetCore.Identity;
using Microsoft.EntityFrameworkCore;
using ScpCv.Domain.Model;
using ScpCv.Infrastructure.Persistence;

namespace ScpCv.Infrastructure.Auth;

public sealed class DevelopmentAccountSeeder(
    WriteCoordinator writes,
    IPasswordHasher<UserAccount> passwordHasher,
    ScpCvAuthenticationOptions options)
{
    public async Task SeedAsync(CancellationToken cancellationToken = default)
    {
        var seed = options.DevelopmentAccount;
        var username = seed.Username.Trim();
        if (username.Length == 0 || seed.Password.Length == 0)
        {
            return;
        }

        await writes.ExecuteAsync(
            async (database, token) =>
            {
                if (await database.UserAccounts.AnyAsync(user => user.Username == username, token)
                    .ConfigureAwait(false))
                {
                    return;
                }

                var user = new UserAccount
                {
                    Username = username,
                    IsActive = true,
                    IsStaff = seed.IsStaff,
                    IsSuperuser = seed.IsSuperuser,
                    PermissionsJson = JsonSerializer.Serialize(seed.Permissions.Distinct(StringComparer.Ordinal)),
                };
                user.PasswordHash = passwordHasher.HashPassword(user, seed.Password);
                database.UserAccounts.Add(user);
            },
            cancellationToken).ConfigureAwait(false);
    }
}
