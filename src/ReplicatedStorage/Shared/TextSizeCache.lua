-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:20:07 PM
-- Cached decompilation

local s_TextService_0 = game:GetService("TextService")
local v1 = require(game.ReplicatedStorage.Shared.LRU)
local v2 = {
    ["DEFAULT_SIZE_BOUNDS"] = Vector2.new(10000, 10000)
}
local v_u_3 = v1.new(200)
v2.get_text_size = function(_, p4, p5, p6, p7) --[[ Name: get_text_size ]] --[[ Line: 10 ]]
    --[[ Upvalues: (copy 1): v_u_3, (copy 2): s_TextService_0 ]]
    local v8 = string.format("(%s)_%s_%s_%s", tostring(p4), tostring(p5), tostring(p6), (tostring(p7)))
    local v9 = v_u_3:get(v8)
    if v9 then
        return v9;
    end;
    local v10 = s_TextService_0:GetTextSize(p4, p5, p6, p7)
    v_u_3:set(v8, v10)
    return v10;
end;
return v2;
