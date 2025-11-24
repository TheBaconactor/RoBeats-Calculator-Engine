-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:20:53 PM
-- Cached decompilation

require(game.ReplicatedStorage.Shared.SPUIChild)
local v_u_1 = require(game.ReplicatedStorage.Menu.SPUIChildButton)
return {
    ["new"] = function(_) --[[ Name: new ]] --[[ Line: 9 ]]
        return {
            ["set_visible"] = function(_, _) end,
            ["load_data"] = function(_, _) end,
            ["refresh"] = function(_) end,
            ["layout"] = function(_) end,
            ["requires_reload_on_menu_refocus"] = function(_) --[[ Name: requires_reload_on_menu_refocus ]] --[[ Line: 15 ]]
                return false;
            end,
            ["behaviour_update"] = function(_, _) end
        };
    end,
    ["create_tab_to_button"] = function(_, p2, p3, p4, p5, p6, p_u_7) --[[ Name: create_tab_to_button ]] --[[ Line: 21 ]]
        --[[ Upvalues: (copy 1): v_u_1 ]]
        p6:add(p2, p3:add_cycle_element(p5, 1, v_u_1:new(p4, p5._spui, function() --[[ Line: 25 ]]
            --[[ Upvalues: (copy 1): p_u_7 ]]
            p_u_7()
        end)):set_auto_zoffset_behaviour(true))
    end
};
