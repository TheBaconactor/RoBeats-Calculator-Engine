-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:20:55 PM
-- Cached decompilation

local v_u_1 = require(game.ReplicatedStorage.Shared.SPDict)
local v2 = {
    ["Recommended"] = 1,
    ["AllMySongs"] = 2,
    ["NowPlaying"] = 3,
    ["ControllerBase"] = {}
}
v2.ControllerBase.new = function(_) --[[ Name: new ]] --[[ Line: 10 ]]
    --[[ Upvalues: (copy 1): v_u_1 ]]
    local v3 = {
        ["set_visible"] = function(_, _) end,
        ["load_data"] = function(_, _) end,
        ["refresh"] = function(_) end,
        ["layout"] = function(_) end,
        ["requires_reload_on_menu_refocus"] = function(_) --[[ Name: requires_reload_on_menu_refocus ]] --[[ Line: 16 ]]
            return false;
        end,
        ["on_clear_filter"] = function(_) end,
        ["get_max_difficulty"] = function(_) --[[ Name: get_max_difficulty ]] --[[ Line: 18 ]]
            return 0;
        end,
        ["behaviour_update"] = function(_, _) end,
        ["get_page_total"] = function(_) --[[ Name: get_page_total ]] --[[ Line: 23 ]]
            return 0;
        end,
        ["on_filter_change_difficulty"] = function(_, _) end
    }
    v3.get_songkey_set = function(_) --[[ Name: get_songkey_set ]] --[[ Line: 19 ]]
        --[[ Upvalues: (ref 1): v_u_1 ]]
        return v_u_1:new();
    end;
    return v3;
end;
return v2;
