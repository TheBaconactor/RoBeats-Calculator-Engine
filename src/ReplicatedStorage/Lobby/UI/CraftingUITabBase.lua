-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:20:52 PM
-- Cached decompilation

local v_u_1 = require(game.ReplicatedStorage.Shared.DebugOut)
return {
    ["new"] = function(_) --[[ Name: new ]] --[[ Line: 6 ]]
        --[[ Upvalues: (copy 1): v_u_1 ]]
        local v2 = {
            ["clear_selected_display"] = function(_) end,
            ["reset_page"] = function(_) end,
            ["is_search_section_enabled"] = function(_) --[[ Name: is_search_section_enabled ]] --[[ Line: 21 ]]
                return false;
            end,
            ["get_category_names"] = function(_) --[[ Name: get_category_names ]] --[[ Line: 22 ]]
                return "Category1", "Category2";
            end,
            ["get_empty_text"] = function(_) --[[ Name: get_empty_text ]] --[[ Line: 23 ]]
                return "";
            end,
            ["show_craft_amount_buttons"] = function(_) --[[ Name: show_craft_amount_buttons ]] --[[ Line: 25 ]]
                return false, false;
            end,
            ["show_use_amount_buttons"] = function(_) --[[ Name: show_use_amount_buttons ]] --[[ Line: 26 ]]
                return false, false;
            end,
            ["craft_amount_button_pressed"] = function(_, _) end
        }
        v2.set_visible = function(_, _) --[[ Name: set_visible ]] --[[ Line: 9 ]]
            --[[ Upvalues: (ref 1): v_u_1 ]]
            v_u_1:warnf("CraftingUITabBase:set_visible not implemented")
        end;
        v2.redraw_list = function(_) --[[ Name: redraw_list ]] --[[ Line: 11 ]]
            --[[ Upvalues: (ref 1): v_u_1 ]]
            v_u_1:warnf("CraftingUITabBase:redraw_list not implemented")
        end;
        v2.page_up = function(_) --[[ Name: page_up ]] --[[ Line: 12 ]]
            --[[ Upvalues: (ref 1): v_u_1 ]]
            v_u_1:warnf("CraftingUITabBase:page_up not implemented")
        end;
        v2.page_down = function(_) --[[ Name: page_down ]] --[[ Line: 13 ]]
            --[[ Upvalues: (ref 1): v_u_1 ]]
            v_u_1:warnf("CraftingUITabBase:page_down not implemented")
        end;
        v2.can_page_up = function(_) --[[ Name: can_page_up ]] --[[ Line: 14 ]]
            --[[ Upvalues: (ref 1): v_u_1 ]]
            v_u_1:warnf("CraftingUITabBase:can_page_up not implemented")
            return false;
        end;
        v2.can_page_down = function(_) --[[ Name: can_page_down ]] --[[ Line: 15 ]]
            --[[ Upvalues: (ref 1): v_u_1 ]]
            v_u_1:warnf("CraftingUITabBase:can_page_down not implemented")
            return false;
        end;
        v2.list_element_pressed = function(_, _, _) --[[ Name: list_element_pressed ]] --[[ Line: 16 ]]
            --[[ Upvalues: (ref 1): v_u_1 ]]
            v_u_1:warnf("CraftingUITabBase:list_element_pressed not implemented")
        end;
        v2.craft_pressed = function(_) --[[ Name: craft_pressed ]] --[[ Line: 17 ]]
            --[[ Upvalues: (ref 1): v_u_1 ]]
            v_u_1:warnf("CraftingUITabBase:craft pressed not implemented")
        end;
        v2.select_element = function(_, _) --[[ Name: select_element ]] --[[ Line: 18 ]]
            --[[ Upvalues: (ref 1): v_u_1 ]]
            v_u_1:warnf("CraftingUITabBase:select_element not implemented")
        end;
        return v2;
    end
};
