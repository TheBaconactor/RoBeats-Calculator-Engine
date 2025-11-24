-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:20:08 PM
-- Cached decompilation

local v_u_1 = require(game.ReplicatedStorage.Shared.AssertType)
require(game.ReplicatedStorage.Shared.SPUtil)
local v_u_2 = require(game.ReplicatedStorage.Shared.SPList)
local v_u_3 = require(game.ReplicatedStorage.Shared.Bit)
local v_u_4 = {
    ["Type"] = "NoteSkinColor"
}
v_u_4.new = function(_, p_u_5, p_u_6, p_u_7) --[[ Name: new ]] --[[ Line: 9 ]]
    --[[ Upvalues: (copy 1): v_u_4, (copy 2): v_u_1, (copy 3): v_u_3 ]]
    local v8 = {
        ["Type"] = v_u_4.Type
    }
    v_u_1:is_int(p_u_5)
    v_u_1:is_int(p_u_6)
    v_u_1:is_int(p_u_7)
    v8.get_rgb = function(_) --[[ Name: get_rgb ]] --[[ Line: 17 ]]
        --[[ Upvalues: (ref 1): p_u_5, (ref 2): p_u_6, (ref 3): p_u_7 ]]
        return p_u_5, p_u_6, p_u_7;
    end;
    v8.to_table = function(_) --[[ Name: to_table ]] --[[ Line: 19 ]]
        --[[ Upvalues: (ref 1): p_u_5, (ref 2): p_u_6, (ref 3): p_u_7 ]]
        return {
            ["r"] = p_u_5,
            ["g"] = p_u_6,
            ["b"] = p_u_7
        };
    end;
    local v_u_9 = nil
    v8.to_color3 = function(_) --[[ Name: to_color3 ]] --[[ Line: 28 ]]
        --[[ Upvalues: (ref 1): v_u_9, (ref 2): p_u_5, (ref 3): p_u_6, (ref 4): p_u_7 ]]
        if v_u_9 == nil then
            v_u_9 = Color3.fromRGB(p_u_5, p_u_6, p_u_7)
        end;
        return v_u_9;
    end;
    v8.to_int32 = function(_) --[[ Name: to_int32 ]] --[[ Line: 35 ]]
        --[[ Upvalues: (ref 1): v_u_3, (ref 2): p_u_5, (ref 3): p_u_6, (ref 4): p_u_7 ]]
        return v_u_3.Or(v_u_3.Or(v_u_3.LShift(p_u_5, 0), v_u_3.LShift(p_u_6, 8)), v_u_3.LShift(p_u_7, 16));
    end;
    v8.set_rgb = function(_, p10, p11, p12) --[[ Name: set_rgb ]] --[[ Line: 47 ]]
        --[[ Upvalues: (ref 1): p_u_5, (ref 2): p_u_6, (ref 3): p_u_7, (ref 4): v_u_9 ]]
        p_u_5 = p10
        p_u_6 = p11
        p_u_7 = p12
        v_u_9 = nil
    end;
    return v8;
end;
v_u_4.from_table = function(_, p13) --[[ Name: from_table ]] --[[ Line: 55 ]]
    --[[ Upvalues: (copy 1): v_u_4 ]]
    return v_u_4:new(p13.r, p13.g, p13.b);
end;
local v_u_14 = v_u_4:new(254, 226, 19)
local v_u_15 = v_u_4:new(95, 244, 255)
v_u_4.get_default_base_color = function(_) --[[ Name: get_default_base_color ]] --[[ Line: 62 ]]
    --[[ Upvalues: (copy 1): v_u_14 ]]
    return v_u_14;
end;
v_u_4.get_default_fever_color = function(_) --[[ Name: get_default_fever_color ]] --[[ Line: 63 ]]
    --[[ Upvalues: (copy 1): v_u_15 ]]
    return v_u_15;
end;
v_u_4.from_int32 = function(_, p16) --[[ Name: from_int32 ]] --[[ Line: 65 ]]
    --[[ Upvalues: (copy 1): v_u_3, (copy 2): v_u_4 ]]
    return v_u_4:new(v_u_3.And(p16, 255), v_u_3.And(v_u_3.RShift(p16, 8), 255), (v_u_3.And(v_u_3.RShift(p16, 16), 255)));
end;
v_u_4.note_basecolor_list_from_playerblob = function(_, p17) --[[ Name: note_basecolor_list_from_playerblob ]] --[[ Line: 72 ]]
    --[[ Upvalues: (copy 1): v_u_2, (copy 2): v_u_4 ]]
    local v18 = v_u_2:new()
    v18:push_back(v_u_4:from_int32(p17.BaseColor1))
    v18:push_back(v_u_4:from_int32(p17.BaseColor2))
    v18:push_back(v_u_4:from_int32(p17.BaseColor3))
    v18:push_back(v_u_4:from_int32(p17.BaseColor4))
    return v18;
end;
v_u_4.note_fevercolor_list_from_playerblob = function(_, p19) --[[ Name: note_fevercolor_list_from_playerblob ]] --[[ Line: 82 ]]
    --[[ Upvalues: (copy 1): v_u_2, (copy 2): v_u_4 ]]
    local v20 = v_u_2:new()
    v20:push_back(v_u_4:from_int32(p19.FeverColor1))
    v20:push_back(v_u_4:from_int32(p19.FeverColor2))
    v20:push_back(v_u_4:from_int32(p19.FeverColor3))
    v20:push_back(v_u_4:from_int32(p19.FeverColor4))
    return v20;
end;
return v_u_4;
