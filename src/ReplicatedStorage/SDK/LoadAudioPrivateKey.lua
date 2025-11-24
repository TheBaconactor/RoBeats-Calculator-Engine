-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:20:31 PM
-- Cached decompilation

require(game.ReplicatedStorage.Shared.DebugOut)
local s_ContentProvider_0 = game:GetService("ContentProvider")
return {
    ["load_private_keys"] = function(_, p1) --[[ Name: load_private_keys ]] --[[ Line: 6 ]]
        --[[ Upvalues: (copy 1): s_ContentProvider_0 ]]
        for _, v2 in pairs(p1) do
            s_ContentProvider_0:RegisterSessionEncryptedAsset(v2.AssetId, v2.ScrambledKey)
        end;
    end
};
