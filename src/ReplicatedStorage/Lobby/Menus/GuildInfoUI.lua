-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:20:45 PM
-- Cached decompilation

local v_u_1 = require(game.ReplicatedStorage.Shared.SPUtil)
require(game.ReplicatedStorage.Shared.SPDict)
require(game.ReplicatedStorage.Shared.SPList)
require(game.ReplicatedStorage.Shared.SPUISystem)
local v_u_2 = require(game.ReplicatedStorage.Menu.MenuBase)
local v_u_3 = require(game.ReplicatedStorage.Shared.SPUIChild)
local v_u_4 = require(game.ReplicatedStorage.Menu.SPUIChildButton)
local v_u_5 = require(game.ReplicatedStorage.Shared.DebugOut)
local v_u_6 = require(game.ReplicatedStorage.Local.SFXManager)
local v_u_7 = require(game.ReplicatedStorage.Shared.SPRemoteEvent)
local v_u_8 = require(game.ReplicatedStorage.LocalShared.EnvironmentSetup)
local v_u_9 = require(game.ReplicatedStorage.PlayerInfo.PlayerBlob)
local v_u_10 = require(game.ReplicatedStorage.Shared.GuildUtil)
local v_u_11 = require(game.ReplicatedStorage.LocalShared.PurchaseRedirect)
local v_u_12 = require(game.ReplicatedStorage.Shared.GuildData)
local v_u_13 = require(game.ReplicatedStorage.Lobby.Dialogue.GuildDialogue)
local v_u_14 = require(game.ReplicatedStorage.Menu.MenuSystem)
local v15 = require(game.ReplicatedStorage.Shared.Dependency)
local v_u_16 = nil
local v_u_17 = nil
local v_u_18 = nil
v15:require_client(function() --[[ Line: 24 ]]
    --[[ Upvalues: (ref 1): v_u_16, (ref 2): v_u_17, (ref 3): v_u_18 ]]
    v_u_16 = require(game.ReplicatedStorage.Menu.PopupMessageUI)
    v_u_17 = require(game.ReplicatedStorage.Lobby.Menus.GuildRecruitmentUI)
    v_u_18 = require(game.ReplicatedStorage.Menu.ScreenGuiTextBoxUI)
end)
return {
    ["new"] = function(_, p_u_19, p_u_20, p_u_21) --[[ Name: new ]] --[[ Line: 33 ]]
        --[[ Upvalues: (copy 1): v_u_2, (copy 2): v_u_1, (copy 3): v_u_8, (copy 4): v_u_13, (copy 5): v_u_10, (copy 6): v_u_9, (copy 7): v_u_4, (copy 8): v_u_3, (copy 9): v_u_6, (ref 10): v_u_17, (ref 11): v_u_16, (ref 12): v_u_18, (copy 13): v_u_7, (copy 14): v_u_12, (copy 15): v_u_5, (copy 16): v_u_11, (copy 17): v_u_14 ]]
        local v22 = v_u_2:new(p_u_20, p_u_21)
        local v_u_23 = nil
        local v_u_24 = nil
        v22.cons = function(p_u_25) --[[ Name: cons ]] --[[ Line: 39 ]]
            --[[ Upvalues: (ref 1): v_u_23, (ref 2): v_u_1, (ref 3): v_u_8, (ref 4): v_u_24, (ref 5): v_u_13, (copy 6): p_u_19, (ref 7): v_u_10, (ref 8): v_u_9, (ref 9): v_u_4, (ref 10): v_u_3, (copy 11): p_u_20, (ref 12): v_u_6, (copy 13): p_u_21, (ref 14): v_u_17 ]]
            v_u_23 = game.ReplicatedStorage.LobbyElementProtos.WorldUIProto.Guild.GuildInfoUI:Clone()
            v_u_23.Name = v_u_1:gen_name(v_u_23.Name)
            v_u_23.Parent = v_u_8:get_world_ui_folder()
            p_u_25._native_size = v_u_23.PrimaryPart.Size
            p_u_25._size = p_u_25._native_size
            v_u_24 = v_u_13:new(p_u_19, p_u_25, p_u_25, v_u_23)
            v_u_23.CreateGuildButton.SurfaceGui.Frame.CurrencyDisplay.Text = tostring(v_u_10:get_guild_creation_cost())
            v_u_9:currency_type_render_icon(v_u_10:get_guild_creation_cost_type(), v_u_23.CreateGuildButton.SurfaceGui.Frame.CurrencyIcon)
            p_u_25:add_cycle_element(p_u_19, 1, v_u_4:new(v_u_3:new(p_u_25, v_u_23.PrimaryPart, v_u_23.BackButtonSurface), p_u_20, function() --[[ Line: 55 ]]
                --[[ Upvalues: (ref 1): p_u_19, (ref 2): v_u_6, (ref 3): p_u_21, (copy 4): p_u_25 ]]
                p_u_19._sfx_manager:play_sfx(v_u_6.SFX_MENU_CLOSE)
                p_u_21:remove_menu(p_u_25)
            end))
            p_u_25:add_cycle_element(p_u_19, 1, v_u_4:new(v_u_3:new(p_u_25, v_u_23.PrimaryPart, v_u_23.CreateGuildButton), p_u_20, function() --[[ Line: 64 ]]
                --[[ Upvalues: (ref 1): p_u_19, (ref 2): v_u_6, (copy 3): p_u_25 ]]
                p_u_19._sfx_manager:play_sfx(v_u_6.SFX_BUTTONPRESS)
                p_u_25:create_guild_action()
            end))
            p_u_25:add_cycle_element(p_u_19, 1, v_u_4:new(v_u_3:new(p_u_25, v_u_23.PrimaryPart, v_u_23.GuildRecruitmentButton), p_u_20, function() --[[ Line: 73 ]]
                --[[ Upvalues: (ref 1): p_u_19, (ref 2): v_u_6, (ref 3): v_u_17, (ref 4): p_u_20, (ref 5): p_u_21, (copy 6): p_u_25 ]]
                p_u_19._sfx_manager:play_sfx(v_u_6.SFX_BUTTONPRESS)
                v_u_17:show_recruiting_teams_ui(p_u_19, p_u_20, p_u_21)
                p_u_21:remove_menu(p_u_25)
            end))
            p_u_25:transition_update_visual(0)
            p_u_25:layout()
        end;
        v22.create_guild_action = function(p_u_26) --[[ Name: create_guild_action ]] --[[ Line: 84 ]]
            --[[ Upvalues: (copy 1): p_u_19, (ref 2): v_u_16, (ref 3): v_u_18, (ref 4): v_u_10, (ref 5): v_u_7, (ref 6): v_u_12, (ref 7): v_u_5, (ref 8): v_u_6, (copy 9): p_u_21, (ref 10): v_u_11 ]]
            local function f_show_error(p27) --[[ Name: show_error ]] --[[ Line: 85 ]]
                --[[ Upvalues: (ref 1): p_u_19, (ref 2): v_u_16 ]]
                p_u_19._menus:push_menu(v_u_16:new(p_u_19, p_u_19._spui, p_u_19._menus):set_text("Cannot create team", p27))
            end;
            local function f_do_purchase() --[[ Name: do_purchase ]] --[[ Line: 89 ]]
                --[[ Upvalues: (ref 1): p_u_19, (copy 2): f_show_error, (ref 3): v_u_18, (ref 4): v_u_10, (ref 5): v_u_16, (ref 6): v_u_7, (ref 7): v_u_12, (ref 8): v_u_5, (ref 9): v_u_6, (ref 10): p_u_21, (copy 11): p_u_26 ]]
                if p_u_19._guild_manager:player_has_guild() then
                    return f_show_error("Already in team");
                end;
                v_u_18:show_text_input_box_ui(p_u_19, "Enter Team Name", string.format("Enter the name of your new team.\nRequirements: %d to %d characters, numbers and letters only.\nAll names are run through Roblox moderation.", v_u_10:guild_name_min_length(), v_u_10:guild_name_max_length()), "", function(p_u_28) --[[ Line: 102 ]]
                    --[[ Upvalues: (ref 1): v_u_10, (ref 2): f_show_error, (ref 3): p_u_19, (ref 4): v_u_16, (ref 5): v_u_7, (ref 6): v_u_12, (ref 7): v_u_5, (ref 8): v_u_6, (ref 9): p_u_21, (ref 10): p_u_26 ]]
                    if #p_u_28 < v_u_10:guild_name_min_length() then
                        return f_show_error("Team name must be 3 or more characters.");
                    end;
                    local v_u_29 = p_u_19._menus:push_menu(v_u_16:new(p_u_19, p_u_19._spui, p_u_19._menus):set_text("Loading...", "Please wait..."):set_close_button_visible(false))
                    p_u_19._evt:wait_on_event_once(v_u_7.EVT_Guild_CreateGuild_ServerResponse, function(p_u_30, p_u_31, p_u_32) --[[ Line: 105 ]]
                        --[[ Upvalues: (ref 1): p_u_19, (ref 2): v_u_12, (copy 3): v_u_29, (ref 4): f_show_error, (ref 5): v_u_5, (copy 6): p_u_28, (ref 7): v_u_6, (ref 8): p_u_21, (ref 9): p_u_26, (ref 10): v_u_16 ]]
                        p_u_19._player_blob_manager:do_sync(function(_) --[[ Line: 106 ]]
                            --[[ Upvalues: (ref 1): v_u_12, (copy 2): p_u_32, (ref 3): p_u_19, (ref 4): v_u_29, (copy 5): p_u_30, (ref 6): f_show_error, (copy 7): p_u_31, (ref 8): v_u_5, (ref 9): p_u_28, (ref 10): v_u_6, (ref 11): p_u_21, (ref 12): p_u_26, (ref 13): v_u_16 ]]
                            local v33 = v_u_12:from_table(p_u_32):get_guildid()
                            p_u_19._menus:remove_menu(v_u_29)
                            if p_u_30 ~= true then
                                return f_show_error(p_u_31);
                            end;
                            v_u_5:puts("Created new guild[%d](%s)", v33, p_u_28)
                            p_u_19._sfx_manager:play_sfx(v_u_6.SFX_ACQUIRE)
                            p_u_21:remove_menu(p_u_26)
                            p_u_19._menus:push_menu(v_u_16:new(p_u_19, p_u_19._spui, p_u_19._menus):set_text("Created new team!", string.format("Created new team \'%s\'!\nTime to invite some other members.", p_u_28))):set_on_close_fn(function() --[[ Line: 118 ]]
                                --[[ Upvalues: (ref 1): p_u_19 ]]
                                p_u_19._guild_manager:show_guild_info_action(p_u_19)
                            end)
                        end)
                    end)
                    p_u_19._evt:fire_event_to_server(v_u_7.EVT_Guild_CreateGuild_Client, p_u_28)
                end):set_text_box_empty_text("Team Name"):set_max_length(v_u_10:guild_name_max_length())
            end;
            local v34 = v_u_11:playerblob_purchase_needs_redirect(p_u_19._player_blob_manager:get_player_blob(), v_u_10:get_guild_creation_cost_type(), v_u_10:get_guild_creation_cost())
            if v34:is_valid() then
                v_u_11:show_purchase_redirect(p_u_19, v34, function(p35) --[[ Line: 131 ]]
                    --[[ Upvalues: (copy 1): f_do_purchase ]]
                    if p35 then
                        f_do_purchase()
                    end;
                end)
            else
                f_do_purchase()
            end;
        end;
        v22.visual_update = function(p36, p37, p38) --[[ Name: visual_update ]] --[[ Line: 142 ]]
            --[[ Upvalues: (copy 1): p_u_19 ]]
            if p_u_19:transition_local_camera_cframe_finished() ~= false then
                p36:visual_update_base(p37, p38)
            end;
        end;
        v22.behaviour_update = function(p39, p40, p41) --[[ Name: behaviour_update ]] --[[ Line: 149 ]]
            --[[ Upvalues: (ref 1): v_u_14, (ref 2): v_u_24 ]]
            p39:behaviour_update_base(p40, p41)
            if p39._current_mode == v_u_14.MODE_OPEN then
                v_u_24:update(p40)
            end;
        end;
        v22.do_remove = function(_, _) --[[ Name: do_remove ]] --[[ Line: 156 ]]
            --[[ Upvalues: (ref 1): v_u_23 ]]
            v_u_23:Destroy()
        end;
        local v_u_42 = 1
        local v_u_43 = 1
        v22.layout = function(p44) --[[ Name: layout ]] --[[ Line: 162 ]]
            --[[ Upvalues: (copy 1): p_u_20, (ref 2): v_u_43, (ref 3): v_u_23, (ref 4): v_u_24 ]]
            p44:opt_rescale_to_max_nxy(p_u_20, 0.8, 0.8, v_u_43)
            local v45, v46 = p44:opt_update_cframe_params(p_u_20, {
                ["PositionNXY"] = Vector2.new(0.5, 0.5),
                ["OffsetXYZ"] = p44:anchored_offset(0.5, 0.5),
                ["LocalRotationOffset"] = Vector3.new(0, 0, 0)
            })
            if v45 == true then
                v_u_23:SetPrimaryPartCFrame(v46)
            end;
            v_u_24:layout()
        end;
        v22.set_alpha = function(_, p47) --[[ Name: set_alpha ]] --[[ Line: 175 ]]
            --[[ Upvalues: (ref 1): v_u_42, (ref 2): v_u_1, (ref 3): v_u_23 ]]
            if v_u_42 ~= p47 then
                v_u_42 = p47
                v_u_1:r_set_alpha(v_u_23, v_u_42)
            end;
        end;
        v22.get_alpha = function(_) --[[ Name: get_alpha ]] --[[ Line: 181 ]]
            --[[ Upvalues: (ref 1): v_u_42 ]]
            return v_u_42;
        end;
        v22.set_scale = function(_, p48) --[[ Name: set_scale ]] --[[ Line: 182 ]]
            --[[ Upvalues: (ref 1): v_u_43 ]]
            v_u_43 = p48
        end;
        v22.get_scale = function(_) --[[ Name: get_scale ]] --[[ Line: 183 ]]
            --[[ Upvalues: (ref 1): v_u_43 ]]
            return v_u_43;
        end;
        v22.get_native_size = function(p49) --[[ Name: get_native_size ]] --[[ Line: 185 ]]
            return p49._native_size;
        end;
        v22.get_size = function(p50) --[[ Name: get_size ]] --[[ Line: 188 ]]
            return p50._size;
        end;
        v22.set_size = function(p51, p52) --[[ Name: set_size ]] --[[ Line: 191 ]]
            --[[ Upvalues: (ref 1): v_u_23 ]]
            p51._size = p52
            v_u_23.PrimaryPart.Size = Vector3.new(p52.X, p52.Y, 0)
        end;
        v22.get_pos = function(_) --[[ Name: get_pos ]] --[[ Line: 195 ]]
            --[[ Upvalues: (ref 1): v_u_23 ]]
            return v_u_23.PrimaryPart.Position;
        end;
        v22.get_sgui = function(_) --[[ Name: get_sgui ]] --[[ Line: 198 ]]
            --[[ Upvalues: (ref 1): v_u_23 ]]
            return v_u_23.PrimaryPart.SurfaceGui;
        end;
        v22:cons()
        return v22;
    end
};
