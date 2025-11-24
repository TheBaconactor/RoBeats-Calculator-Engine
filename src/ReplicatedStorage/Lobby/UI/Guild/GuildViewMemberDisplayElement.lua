-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:20:57 PM
-- Cached decompilation

local v_u_1 = require(game.ReplicatedStorage.Shared.SPUtil)
require(game.ReplicatedStorage.Shared.CurveUtil)
require(game.ReplicatedStorage.Shared.SPDict)
require(game.ReplicatedStorage.Shared.SPList)
require(game.ReplicatedStorage.Shared.SPUISystem)
require(game.ReplicatedStorage.Menu.MenuBase)
local v_u_2 = require(game.ReplicatedStorage.Shared.SPUIChild)
local v_u_3 = require(game.ReplicatedStorage.Menu.SPUIChildButton)
require(game.ReplicatedStorage.Shared.DebugOut)
local v_u_4 = require(game.ReplicatedStorage.Shared.DebugConfig)
local v_u_5 = require(game.ReplicatedStorage.Local.SFXManager)
local v_u_6 = require(game.ReplicatedStorage.Shared.GuildRank)
local v_u_7 = require(game.ReplicatedStorage.Shared.GuildData)
local v_u_8 = require(game.ReplicatedStorage.Shared.GuildUtil)
local v_u_9 = require(game.ReplicatedStorage.Shared.SPRemoteEvent)
local v_u_10 = require(game.ReplicatedStorage.Menu.PopupMessageUI)
local v11 = require(game.ReplicatedStorage.Shared.Dependency)
local v_u_12 = nil
v11:require_client(function() --[[ Line: 20 ]]
    --[[ Upvalues: (ref 1): v_u_12 ]]
    v_u_12 = require(game.ReplicatedStorage.Lobby.Menus.GuildMemberEditPopupUI)
end)
return {
    ["new"] = function(_, p_u_13, p_u_14, p_u_15) --[[ Name: new ]] --[[ Line: 26 ]]
        --[[ Upvalues: (copy 1): v_u_7, (copy 2): v_u_8, (copy 3): v_u_6, (copy 4): v_u_2, (copy 5): v_u_3, (copy 6): v_u_5, (ref 7): v_u_12, (copy 8): v_u_10, (copy 9): v_u_9, (copy 10): v_u_1, (copy 11): v_u_4 ]]
        local v16 = {}
        local v_u_17 = nil
        local v_u_18 = nil
        local v_u_19 = nil
        local v_u_20 = nil
        local v_u_21 = nil
        local v_u_22 = nil
        local v_u_23 = nil
        local v_u_24 = nil
        local v_u_25 = nil
        local v_u_26 = v_u_7.MemberInfo:new(v_u_8:invalid_rbxid(), "", v_u_6.Member)
        v16.get_display_member_info = function(_) --[[ Name: get_display_member_info ]] --[[ Line: 38 ]]
            --[[ Upvalues: (ref 1): v_u_26 ]]
            return v_u_26;
        end;
        v16.cons = function(_) --[[ Name: cons ]] --[[ Line: 40 ]]
            --[[ Upvalues: (ref 1): v_u_17, (ref 2): v_u_2, (copy 3): p_u_14, (copy 4): p_u_15, (ref 5): v_u_18, (copy 6): p_u_13, (ref 7): v_u_3, (ref 8): v_u_5, (ref 9): v_u_26, (ref 10): v_u_8, (ref 11): v_u_12, (ref 12): v_u_19, (ref 13): v_u_10, (ref 14): v_u_9, (ref 15): v_u_20, (ref 16): v_u_21, (ref 17): v_u_22, (ref 18): v_u_23, (ref 19): v_u_24, (ref 20): v_u_25, (ref 21): v_u_1 ]]
            v_u_17 = v_u_2:new(p_u_14, p_u_14:get_uichild_parent(), p_u_15.MainSurface):set_default_sgui()
            v_u_18 = p_u_14:add_cycle_element(p_u_13, 1, v_u_3:new(v_u_2:new(v_u_17, p_u_15.MainSurface, p_u_15.EditIconButton), p_u_13._spui, function() --[[ Line: 45 ]]
                --[[ Upvalues: (ref 1): p_u_13, (ref 2): v_u_5, (ref 3): v_u_26, (ref 4): v_u_8, (ref 5): v_u_12, (ref 6): p_u_14 ]]
                p_u_13._sfx_manager:play_sfx(v_u_5.SFX_BUTTONPRESS)
                if v_u_26:get_rbxid() ~= v_u_8:invalid_rbxid() then
                    p_u_13._menus:push_menu(v_u_12:new(p_u_13, p_u_14, v_u_26))
                end;
            end))
            v_u_19 = p_u_14:add_cycle_element(p_u_13, 1, v_u_3:new(v_u_2:new(v_u_17, p_u_15.MainSurface, p_u_15.TeleportButton), p_u_13._spui, function() --[[ Line: 57 ]]
                --[[ Upvalues: (ref 1): p_u_13, (ref 2): v_u_5, (ref 3): v_u_26, (ref 4): v_u_10, (ref 5): v_u_9 ]]
                p_u_13._sfx_manager:play_sfx(v_u_5.SFX_BUTTONPRESS)
                if v_u_26 then
                    local l__spui_0 = p_u_13._spui
                    local l__menus_0 = p_u_13._menus
                    l__menus_0:push_menu(v_u_10:new(p_u_13, l__spui_0, l__menus_0):set_text("Please Wait..", "Teleporting"))
                    p_u_13._evt:fire_event_to_server(v_u_9.EVT_Guild_TeleportPlayer_Client, v_u_26:get_rbxid())
                end;
            end))
            v_u_19:set_visible(false)
            local l_Frame_0 = p_u_15.MainSurface.SurfaceGui.Frame
            v_u_20 = l_Frame_0.NameDisplay
            v_u_21 = l_Frame_0.RankDisplay
            v_u_22 = l_Frame_0.CurrentWeekContributionPointsDisplay
            v_u_23 = l_Frame_0.LastWeekContributionPointsDisplay
            v_u_24 = l_Frame_0.PlayerIcon
            v_u_25 = l_Frame_0.StatusDisplay
            v_u_25.Text = "Loading..."
            v_u_25.TextColor3 = v_u_1:color3(255, 255, 255)
        end;
        v16.set_display_element = function(_, p27) --[[ Name: set_display_element ]] --[[ Line: 84 ]]
            --[[ Upvalues: (ref 1): v_u_26, (ref 2): v_u_19, (copy 3): p_u_14, (ref 4): v_u_20, (ref 5): v_u_21, (ref 6): v_u_1, (ref 7): v_u_6, (ref 8): v_u_24, (ref 9): v_u_4, (ref 10): v_u_22, (ref 11): v_u_23, (ref 12): v_u_8, (ref 13): v_u_7, (ref 14): v_u_18 ]]
            v_u_26 = p27
            v_u_19:set_visible(false)
            if v_u_26 == nil then
                v_u_26 = v_u_7.MemberInfo:new(v_u_8:invalid_rbxid(), "", v_u_6.Member)
                v_u_18:set_visible(false)
            else
                local v28 = p_u_14:get_guild_data()
                v_u_20.Text = v_u_26:get_name()
                v_u_21.Text = v_u_1:enum_val_to_name(v_u_26:get_rank(), v_u_6)
                if v_u_26:get_rank() == v_u_6.Owner or v_u_26:get_rank() == v_u_6.Admin then
                    v_u_21.TextColor3 = v_u_1:color3(255, 202, 31)
                else
                    v_u_21.TextColor3 = v_u_1:color3(255, 255, 255)
                end;
                v_u_24.Image = v_u_1:transparent_assetid()
                v_u_1:get_user_thumbnail(v_u_26:get_rbxid(), function(p29, _) --[[ Line: 99 ]]
                    --[[ Upvalues: (ref 1): v_u_24 ]]
                    v_u_24.Image = p29
                end, false)
                if v_u_4.HideGuildContributionUIElements == true then
                    v_u_22.Text = "-"
                    v_u_23.Text = "-"
                else
                    v_u_22.Text = v_u_1:comma_value(p27:get_current_week_contribution_points())
                    if p27:get_current_week_contribution_points() >= v_u_8:get_weekly_player_contribution_cap() then
                        v_u_22.Text = v_u_22.Text .. " (Max)"
                    end;
                    if p27:get_joined_week() > v28:get_last_week_contribution_entry():get_week_id() then
                        v_u_23.Text = "-"
                    else
                        v_u_23.Text = v_u_1:comma_value(p27:get_last_week_contribution_points())
                        if p27:get_last_week_contribution_points() >= v_u_8:get_weekly_player_contribution_cap() then
                            v_u_23.Text = v_u_23.Text .. " (Max)"
                        end;
                    end;
                end;
                v_u_18:set_visible(v_u_7:member_can_kick_member(v_u_7:get_player_info(v28, v_u_1:get_local_userid()), v_u_26))
            end;
        end;
        v16.set_status_loading = function(_) --[[ Name: set_status_loading ]] --[[ Line: 131 ]]
            --[[ Upvalues: (ref 1): v_u_25, (ref 2): v_u_1 ]]
            v_u_25.Text = "Loading..."
            v_u_25.TextColor3 = v_u_1:color3(255, 255, 255)
        end;
        v16.set_status = function(_, p30) --[[ Name: set_status ]] --[[ Line: 136 ]]
            --[[ Upvalues: (ref 1): v_u_26, (ref 2): v_u_1, (ref 3): v_u_25, (ref 4): v_u_8, (ref 5): v_u_19 ]]
            if v_u_26:get_rbxid() == v_u_1:get_local_userid() then
                v_u_25.Text = "(You)"
                v_u_25.TextColor3 = v_u_1:color3(255, 255, 255)
                return;
            elseif p30 == v_u_8.Status.Offline then
                v_u_25.Text = "Offline"
                v_u_25.TextColor3 = v_u_1:color3(160, 160, 160)
            else
                if p30 == v_u_8.Status.OnlineDifferentServer then
                    v_u_19:set_visible(true)
                    v_u_25.Text = "Online"
                else
                    v_u_19:set_visible(false)
                    v_u_25.Text = "Online"
                end;
                v_u_25.TextColor3 = v_u_1:color3(154, 255, 38)
            end;
        end;
        v16.set_visible = function(_, p31) --[[ Name: set_visible ]] --[[ Line: 155 ]]
            --[[ Upvalues: (ref 1): v_u_17, (ref 2): v_u_18, (ref 3): v_u_19 ]]
            v_u_17:set_visible(p31)
            v_u_18:set_visible(p31)
            v_u_19:set_visible(p31)
        end;
        v16.layout = function(_) --[[ Name: layout ]] --[[ Line: 161 ]]
            --[[ Upvalues: (ref 1): v_u_17 ]]
            v_u_17:layout()
        end;
        v16:cons()
        return v16;
    end
};
