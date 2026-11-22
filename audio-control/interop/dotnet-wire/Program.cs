// CPU-only interoperability interview of the existing JSON Schema R0 subset.
// Deliberately NOT a general JSON Schema validator or a native audio engine.
using System.Text.Json;
using System.Text.Json.Nodes;
using System.Text.RegularExpressions;

static class Program
{
    static readonly HashSet<string> IgnoredAnnotations =
        new(StringComparer.Ordinal) { "$schema", "$id", "title", "description" };

    static void Check(bool condition, string message)
    {
        if (!condition) throw new InvalidOperationException(message);
    }

    static bool SameValue(JsonElement a, JsonElement b) =>
        a.ValueKind == b.ValueKind && a.GetRawText() == b.GetRawText();

    // The interpreter handles only keywords used in our pinned R0 contract.
    // Any novel keyword must be admitted explicitly rather than silently ignored.
    static bool Validate(JsonElement value, JsonElement schema, JsonElement root)
    {
        if (schema.ValueKind != JsonValueKind.Object) return false;
        foreach (var keyword in schema.EnumerateObject())
        {
            if (IgnoredAnnotations.Contains(keyword.Name)) continue;
            if (keyword.Name is not ("$defs" or "$ref" or "oneOf" or "allOf" or
                    "if" or "then" or "type" or "const" or "enum" or "pattern" or
                    "minimum" or "required" or "properties" or "additionalProperties" or
                    "maxItems" or "items"))
                throw new InvalidOperationException("Unreviewed schema keyword: " + keyword.Name);
        }
        if (schema.TryGetProperty("$ref", out var reference))
        {
            var s = reference.GetString()
                ?? throw new InvalidOperationException("Null $ref rejected");
            Check(s.StartsWith("#/$defs/", StringComparison.Ordinal), "Unsupported $ref");
            var name = s["#/$defs/".Length..];
            return Validate(value, root.GetProperty("$defs").GetProperty(name), root);
        }
        if (schema.TryGetProperty("oneOf", out var alternatives))
        {
            var matches = 0;
            foreach (var s in alternatives.EnumerateArray())
                if (Validate(value, s, root)) matches++;
            if (matches != 1) return false;
        }
        if (schema.TryGetProperty("type", out var type))
        {
            bool accepted = type.GetString() switch
            {
                "object" => value.ValueKind == JsonValueKind.Object,
                "array" => value.ValueKind == JsonValueKind.Array,
                "string" => value.ValueKind == JsonValueKind.String,
                "integer" => value.ValueKind == JsonValueKind.Number && value.TryGetInt64(out _),
                _ => throw new InvalidOperationException("Unsupported JSON Schema type")
            };
            if (!accepted) return false;
        }
        if (schema.TryGetProperty("const", out var c) && !SameValue(value, c))
            return false;
        if (schema.TryGetProperty("enum", out var choices))
        {
            bool matches = false;
            foreach (var choice in choices.EnumerateArray())
                if (SameValue(value, choice)) matches = true;
            if (!matches) return false;
        }
        if (schema.TryGetProperty("minimum", out var min))
        {
            if (value.ValueKind != JsonValueKind.Number ||
                !value.TryGetInt64(out var n) || n < min.GetInt64()) return false;
        }
        if (schema.TryGetProperty("pattern", out var pattern))
        {
            if (value.ValueKind != JsonValueKind.String ||
                !Regex.IsMatch(value.GetString()!, pattern.GetString()!, RegexOptions.CultureInvariant))
                return false;
        }
        if (schema.TryGetProperty("required", out var required))
        {
            if (value.ValueKind != JsonValueKind.Object) return false;
            foreach (var req in required.EnumerateArray())
                if (!value.TryGetProperty(req.GetString()!, out _)) return false;
        }
        if (schema.TryGetProperty("properties", out var properties))
        {
            if (value.ValueKind != JsonValueKind.Object) return false;
            foreach (var property in value.EnumerateObject())
            {
                if (properties.TryGetProperty(property.Name, out var rule))
                {
                    if (!Validate(property.Value, rule, root)) return false;
                }
                else if (schema.TryGetProperty("additionalProperties", out var extra) &&
                    extra.ValueKind == JsonValueKind.False)
                    return false;
            }
        }
        if (schema.TryGetProperty("maxItems", out var cap) &&
            (value.ValueKind != JsonValueKind.Array || value.GetArrayLength() > cap.GetInt32()))
            return false;
        if (schema.TryGetProperty("items", out var itemRule))
        {
            if (value.ValueKind != JsonValueKind.Array) return false;
            foreach (var item in value.EnumerateArray())
                if (!Validate(item, itemRule, root)) return false;
        }
        if (schema.TryGetProperty("allOf", out var allOf))
            foreach (var clause in allOf.EnumerateArray())
                if (!Validate(value, clause, root)) return false;
        if (schema.TryGetProperty("if", out var condition) &&
            Validate(value, condition, root) &&
            schema.TryGetProperty("then", out var consequence) &&
            !Validate(value, consequence, root))
            return false;
        return true;
    }

    static void Main(string[] args)
    {
        Check(args.Length == 1, "Usage: dotnet run --project Probe.csproj -- REPOSITORY_ROOT");
        var root = Path.GetFullPath(args[0]);
        var contract = Path.Combine(root, "audio-control", "contract");
        using var schemaDoc = JsonDocument.Parse(File.ReadAllText(Path.Combine(contract, "audio_control.r0.schema.json")));
        using var casesDoc = JsonDocument.Parse(File.ReadAllText(Path.Combine(contract, "vectors-r0.json")));
        using var ingressDoc = JsonDocument.Parse(File.ReadAllText(Path.Combine(contract, "ingress-r0.json")));
        var schema = schemaDoc.RootElement;
        int valid = 0, invalid = 0, routed = 0;
        foreach (var test in casesDoc.RootElement.EnumerateArray())
        {
            var name = test.GetProperty("name").GetString();
            var expected = test.GetProperty("valid").GetBoolean();
            var actual = Validate(test.GetProperty("value"), schema, schema);
            Check(actual == expected, "C# vs frozen JSON Schema fixture mismatch: " + name);
            if (actual) valid++; else invalid++;
            using var roundtrip = JsonDocument.Parse(test.GetProperty("value").GetRawText());
            Check(Validate(roundtrip.RootElement, schema, schema) == actual,
                "JSON roundtrip changed validity: " + name);
        }
        foreach (var test in ingressDoc.RootElement.EnumerateArray())
        {
            var envelope = test.GetProperty("envelope");
            Check(Validate(envelope, schema, schema), "Ingress fixture not schema valid");
            var trustedHostChannel = test.GetProperty("channel").GetString() == "verified_local_host";
            var isHostEvent = envelope.GetProperty("action").GetString()!.StartsWith("host_", StringComparison.Ordinal);
            var allow = trustedHostChannel == isHostEvent;
            Check(allow == test.GetProperty("allow").GetBoolean(), "Transport boundary differs: " + test.GetProperty("id").GetString());
            routed++;
        }
        // Extra negative tests independent of the fixed corpus: required field
        // absent, explicit null, and forged privilege in an otherwise valid plan.
        var good = JsonNode.Parse(casesDoc.RootElement[0].GetProperty("value").GetRawText())!.AsObject();
        good.Remove("principal_id");
        using var missing = JsonDocument.Parse(good.ToJsonString());
        Check(!Validate(missing.RootElement, schema, schema), "Missing principal admitted");
        good["principal_id"] = null;
        using var nullPrincipal = JsonDocument.Parse(good.ToJsonString());
        Check(!Validate(nullPrincipal.RootElement, schema, schema), "Null principal admitted");
        good["principal_id"] = "human_1";
        good["host_authorized"] = true;
        using var forged = JsonDocument.Parse(good.ToJsonString());
        Check(!Validate(forged.RootElement, schema, schema), "Forged host authorization admitted");

        Check(valid >= 5 && invalid >= 5 && routed >= 7, "Insufficient fixture coverage");
        Console.WriteLine($"PASS .NET 10 independent contract subset: {valid} valid, {invalid} invalid, {routed} ingress vectors; negative missing/null/forged privileges.");
        Console.WriteLine("NOT general JSON Schema validation, host authentication, DSP, on-device audio, or release evidence.");
    }
}
