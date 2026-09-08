using System.Net;
using System.Text;
using System.Text.RegularExpressions;
using Microsoft.AspNetCore.Hosting;
using Microsoft.AspNetCore.Mvc.Testing;
using Microsoft.AspNetCore.Routing;
using Microsoft.Data.Sqlite;
using Microsoft.Extensions.DependencyInjection;

namespace ScpCv.Contracts.Tests;

public sealed partial class OpenApiCoverageTests
{
    [Fact]
    public async Task EveryDocumentedOperationHasAMatchingRuntimeRouteAndObservedStatus()
    {
        var operations = ReadOperations();
        using var factory = new ContractApplicationFactory();
        using var client = factory.CreateClient(new WebApplicationFactoryClientOptions
        {
            AllowAutoRedirect = false,
            BaseAddress = new Uri("https://localhost"),
        });

        // Build the route catalog without relying on handler names or source layout.
        var runtimeOperations = factory.Services.GetServices<EndpointDataSource>()
            .SelectMany(source => source.Endpoints)
            .OfType<RouteEndpoint>()
            .Where(endpoint => endpoint.RoutePattern.RawText?.StartsWith("/api/", StringComparison.Ordinal) == true)
            .SelectMany(endpoint => (endpoint.Metadata.GetMetadata<IHttpMethodMetadata>()?.HttpMethods ?? [])
                .Select(method => new OperationKey(NormalizePath(endpoint.RoutePattern.RawText!), method.ToUpperInvariant())))
            .ToHashSet();

        var documentedOperations = operations.Select(operation => operation.Key).ToHashSet();
        Assert.Equal(documentedOperations.OrderBy(KeyText), runtimeOperations.OrderBy(KeyText));

        foreach (var operation in operations)
        {
            using var request = new HttpRequestMessage(
                new HttpMethod(operation.Key.Method),
                "/api" + MaterializePath(operation.Path));
            if (operation.Key.Method is "POST" or "PUT" or "PATCH")
            {
                request.Content = new StringContent("{}", Encoding.UTF8, "application/json");
            }

            using var response = await client.SendAsync(request);
            Assert.NotEqual(HttpStatusCode.NotFound, response.StatusCode);
            Assert.NotEqual(HttpStatusCode.MethodNotAllowed, response.StatusCode);
            Assert.True(
                response.StatusCode == HttpStatusCode.Unauthorized || operation.StatusCodes.Contains((int)response.StatusCode),
                $"{operation.Key.Method} {operation.Path} 返回 {(int)response.StatusCode}，不在 OpenAPI 响应集合 [{string.Join(", ", operation.StatusCodes)}] 中。");
        }
    }

    private static List<OpenApiOperation> ReadOperations()
    {
        var openApiRoot = Path.Combine(AppContext.BaseDirectory, "OpenApi");
        var rootLines = File.ReadAllLines(Path.Combine(openApiRoot, "openapi.yaml"));
        var operations = new List<OpenApiOperation>();
        for (var index = 0; index < rootLines.Length - 1; index++)
        {
            var pathMatch = RootPathLine().Match(rootLines[index]);
            if (!pathMatch.Success)
            {
                continue;
            }

            var referenceMatch = ReferenceLine().Match(rootLines[index + 1]);
            Assert.True(referenceMatch.Success, $"OpenAPI 路径 {pathMatch.Groups["path"].Value} 未使用可解析的 paths 引用。");
            var path = pathMatch.Groups["path"].Value;
            var pathDocument = Path.Combine(openApiRoot, "paths", Path.GetFileName(referenceMatch.Groups["file"].Value));
            var method = string.Empty;
            var statuses = new List<int>();
            foreach (var line in File.ReadLines(pathDocument))
            {
                var methodMatch = MethodLine().Match(line);
                if (methodMatch.Success)
                {
                    AddOperation();
                    method = methodMatch.Groups["method"].Value.ToUpperInvariant();
                    statuses.Clear();
                    continue;
                }

                var statusMatch = StatusLine().Match(line);
                if (method.Length > 0 && statusMatch.Success)
                {
                    statuses.Add(int.Parse(statusMatch.Groups["status"].Value, System.Globalization.CultureInfo.InvariantCulture));
                }
            }

            AddOperation();

            void AddOperation()
            {
                if (method.Length == 0)
                {
                    return;
                }

                Assert.NotEmpty(statuses);
                operations.Add(new OpenApiOperation(
                    new OperationKey(NormalizePath(path), method),
                    path,
                    statuses.ToArray()));
            }
        }

        Assert.NotEmpty(operations);
        return operations;
    }

    private static string NormalizePath(string endpointPath) =>
        Parameter().Replace(endpointPath.StartsWith("/api/", StringComparison.Ordinal) ? endpointPath[4..] : endpointPath, "{}");

    private static string MaterializePath(string path) => Parameter().Replace(path, "1");
    private static string KeyText(OperationKey key) => $"{key.Method} {key.Path}";

    [GeneratedRegex("^  (?<path>/[^:]+):$")]
    private static partial Regex RootPathLine();

    [GeneratedRegex("^    \\$ref: './paths/(?<file>[^']+)'$")]
    private static partial Regex ReferenceLine();

    [GeneratedRegex("^(?<method>get|post|put|patch|delete):$", RegexOptions.IgnoreCase)]
    private static partial Regex MethodLine();

    [GeneratedRegex("^    '(?<status>[1-5][0-9]{2})':$")]
    private static partial Regex StatusLine();

    [GeneratedRegex("\\{[^}]+\\}")]
    private static partial Regex Parameter();

    private sealed record OpenApiOperation(OperationKey Key, string Path, IReadOnlySet<int> StatusCodes)
    {
        public OpenApiOperation(OperationKey key, string path, int[] statusCodes)
            : this(key, path, statusCodes.ToHashSet()) { }
    }

    private sealed record OperationKey(string Path, string Method);
}

internal sealed class ContractApplicationFactory : WebApplicationFactory<Program>
{
    private readonly string _temporaryRoot = Path.Combine(
        Path.GetTempPath(),
        "scp-cv-openapi-tests",
        Guid.NewGuid().ToString("N"));

    protected override void ConfigureWebHost(IWebHostBuilder builder)
    {
        builder.UseEnvironment("Testing");
        builder.UseSetting("DataRoot", _temporaryRoot);
        builder.UseSetting("SafetyMode", "Simulation");
        builder.UseSetting("Authentication:DevelopmentAccount:Username", "operator");
        builder.UseSetting("Authentication:DevelopmentAccount:Password", "Contract-password-123");
    }

    protected override void Dispose(bool disposing)
    {
        base.Dispose(disposing);
        if (!disposing)
        {
            return;
        }

        SqliteConnection.ClearAllPools();
        if (Directory.Exists(_temporaryRoot))
        {
            Directory.Delete(_temporaryRoot, recursive: true);
        }
    }
}
