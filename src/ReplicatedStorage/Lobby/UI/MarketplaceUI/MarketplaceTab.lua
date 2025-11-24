-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:20:55 PM
-- Cached decompilation

local v_u_1 = require(game.ReplicatedStorage.Shared.DebugOut)
return {
    ["Tab"] = {
        ["Market"] = 1,
        ["MySales"] = 2
    },
    ["new"] = function(_) --[[ Name: new ]] --[[ Line: 10 ]]
        --[[ Upvalues: (copy 1): v_u_1 ]]
        local v2 = {
            ["layout"] = function(_) end,
            ["behaviour_update"] = function(_, _) end,
            ["sort_buttons_update_mode"] = function(_) end,
            ["on_sort_button_index_pressed"] = function(_, _) end
        }
        v2.get_tab = function(_) --[[ Name: get_tab ]] --[[ Line: 13 ]]
            --[[ Upvalues: (ref 1): v_u_1 ]]
            v_u_1:errf("MarketplaceTab:get_tab() must implement")
        end;
        v2.set_visible = function(_, _) --[[ Name: set_visible ]] --[[ Line: 14 ]]
            --[[ Upvalues: (ref 1): v_u_1 ]]
            v_u_1:errf("MarketplaceTab:set_visible(val) must implement")
        end;
        return v2;
    end
};
